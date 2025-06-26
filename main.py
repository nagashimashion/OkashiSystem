# ==============================================================================
# ライブラリのインポート
# ==============================================================================
# Tkinter: Python標準のGUIライブラリ。画面の作成やボタンの配置などに使用。
import tkinter as tk
from tkinter import font, messagebox

# gspread: Googleスプレッドシートを操作するためのライブラリ。
import gspread
from google.oauth2.service_account import Credentials

# その他、日付や時間、システム関連の標準ライブラリ
from datetime import datetime
import time
import sys


# ==============================================================================
# 全体設定
# ==============================================================================
# Google Cloudからダウンロードしたサービスアカウントの認証キーファイル名 キオスクで使用する場合フルバススで指定すること
# 注意: このファイルは絶対に公開しないこと。セキュリティ上のリスクがあります。
SERVICE_ACCOUNT_FILE = './useful-figure-462606-f3-d5bf8344ee64.json'
# 操作対象のGoogleスプレッドシートのファイル名
SPREADSHEET_NAME = '購買部在庫管理システム'
# APIの操作範囲（スコープ）。この設定でOK。
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']


# ==============================================================================
# アプリケーション本体のクラス定義
# ==============================================================================
class App(tk.Tk):
    """
    在庫管理システムのGUIアプリケーション全体を管理するクラス。
    tk.Tkを継承して、ウィンドウそのものとして振る舞う。
    """
    def __init__(self):
        # 親クラス(tk.Tk)の初期化処理を呼び出す
        super().__init__()

        # --- インスタンス変数の初期化 ---
        # 直前の取引情報（JANコード、マスタシートの行番号、ログデータ）を保存するための変数。取り消し処理で使用。
        self.last_transaction = None

        # --- ウィンドウの基本設定 ---
        self.title("在庫管理システム")
        # ウィンドウをスクリーン全体に表示する（キオスクモード）
        self.attributes('-fullscreen', True)
        # ウィンドウの背景色を設定
        self.configure(bg='#D0F0C0')

        # --- フォントの定義 ---
        # このセクションでフォントを一元管理することで、後からのデザイン変更が容易になる。
        # 3.5インチ画面(480x320)に最適化したフォントサイズ。
        self.info_font = font.Font(family="Helvetica", size=16)
        self.result_font = font.Font(family="Helvetica", size=22, weight="bold")
        self.button_font = font.Font(family="Helvetica", size=12)

        # --- 動的にテキストを変更するための専用変数 ---
        # .set()メソッドで値を変更すると、この変数を使っているラベルの表示も自動で更新される。
        self.info_text = tk.StringVar(value="スプレッドシートに接続中...")
        self.result_text = tk.StringVar(value="")
        self.entry_text = tk.StringVar()

        # --- GUI部品（ウィジェット）の作成 ---
        # 1. 案内メッセージ用ラベル（画面上部）
        info_label = tk.Label(self, textvariable=self.info_text, font=self.info_font, bg=self.cget('bg'))

        # 2. スキャン結果表示用ラベル（画面中央）
        # wraplength: このピクセル幅を超えたら自動で改行する設定。
        # justify: 複数行になった場合に、文字を中央揃えにする設定。
        result_label = tk.Label(self, textvariable=self.result_text, font=self.result_font, bg=self.cget('bg'), wraplength=460, justify=tk.CENTER)

        # 3. 「取り消し」ボタン（画面下部）
        # command: ボタンが押されたときに呼び出すメソッド（関数）を指定。
        # state: ボタンの状態。tk.DISABLEDで、最初は押せないように設定。
        self.cancel_button = tk.Button(self, text="直前の操作を取り消す", font=self.button_font, command=self.undo_last_transaction, width=18, height=2, state=tk.DISABLED)

        # 4. バーコード入力を受け付ける非表示の入力欄(Entry)
        self.hidden_entry = tk.Entry(self, textvariable=self.entry_text)

        # --- ウィジェットの画面への配置 ---
        # .pack()はウィジェットをウィンドウに「詰めて」配置する命令。padyで上下の余白を指定。
        info_label.pack(pady=25)
        result_label.pack(pady=20, expand=True, fill="both") # expand=Trueで利用可能なスペースを埋めるように配置
        self.cancel_button.pack(side="bottom", pady=20)
        # .place()は絶対座標で配置する命令。画面の外(x=-1000)に配置することで、ユーザーには見えなくする。
        self.hidden_entry.place(x=-1000, y=-1000)

        # --- キーボードイベントの紐付け（バインディング） ---
        # このウィンドウ上で特定のキーが押されたときに、指定したメソッドを呼び出すように設定。
        self.bind('<Return>', self.handle_scan) # Enterキーが押されたらhandle_scanを実行
        self.bind('<Escape>', self.quit_app)   # Escapeキーが押されたらquit_appを実行

        # アプリ起動時に、すぐにスキャナ入力を受け付けられるようにフォーカスを当てる
        self.hidden_entry.focus_set()

        # --- 起動時の初期処理 ---
        # スプレッドシートへの接続を開始
        self.connect_to_sheets()

    def connect_to_sheets(self):
        """スプレッドシートへの接続とシートの取得を行う"""
        try:
            # 認証情報を読み込む
            creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
            # 認証情報を使ってgspreadクライアントを初期化
            gc = gspread.authorize(creds)
            # 指定した名前のスプレッドシートを開く
            spreadsheet = gc.open(SPREADSHEET_NAME)
            # 指定した名前のシート（ワークシート）を取得し、インスタンス変数に保存
            self.master_sheet = spreadsheet.worksheet('商品マスタ')
            self.log_sheet = spreadsheet.worksheet('購入履歴')
            # 接続が成功したら、案内メッセージを更新
            self.info_text.set('商品のバーコードをスキャンしてください')
        except Exception as e:
            # 接続中に何らかのエラーが発生した場合
            self.info_text.set("エラー：接続に失敗しました")
            # エラーダイアログを表示
            messagebox.showerror("接続エラー", f"スプレッドシートに接続できませんでした。\n設定を確認してください。\n\n詳細: {e}")
            # アプリケーションを終了
            self.destroy()

    def handle_scan(self, event=None):
        """Enterキーが押された（＝スキャンが完了した）時のメイン処理"""
        # バーコードリーダーは非常に高速なため、入力が完了するのを確実にするための0.1秒の待ち時間
        time.sleep(0.1)

        # 非表示の入力欄からJANコードを取得し、前後の空白を削除
        jan_code = self.entry_text.get().strip()

        # 入力が空（Enterキーだけ押された場合など）は何もしない
        if not jan_code:
            return

        # 新しいスキャンが始まったので、取り消し情報をリセットし、ボタンを無効化
        self.cancel_button.config(state=tk.DISABLED)
        self.last_transaction = None
        self.info_text.set(f'スキャンしました: {jan_code}')
        self.update_idletasks() # 画面の表示を強制的に更新する

        try:
            # 商品マスタシートのF列(6列目)から、入力されたJANコードと一致するセルを探す
            cell = self.master_sheet.find(jan_code, in_column=6)

            if cell: # セルが見つかった場合
                # 見つかった行の全ての値を取得
                row_values = self.master_sheet.row_values(cell.row)

                # 新しいシート構成に合わせて、各列からデータを取得
                product_name = row_values[0]  # A列(1番目)から商品名を取得
                price = int(row_values[2])    # C列(3番目)から価格を取得
                current_stock = int(row_values[3]) # D列(4番目)から現在の在庫数を取得

                if current_stock > 0: # 在庫が1以上ある場合
                    # 在庫を1減らす
                    new_stock = current_stock - 1
                    # D列(4列目)の在庫数を更新
                    self.master_sheet.update_cell(cell.row, 4, new_stock)

                    # 購入履歴シートに記録するデータを作成
                    timestamp = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
                    quantity = 1 # 1回のスキャンなので数量は1
                    total_amount = price # 合計金額
                    log_data = [timestamp, jan_code, product_name, quantity, total_amount]
                    # 購入履歴シートの最終行に追記
                    self.log_sheet.append_row(log_data)

                    # 結果を画面に表示
                    self.result_text.set(f'{product_name} {price}円\n残り: {new_stock}個')

                    # 取り消し機能のために、成功した取引情報を保存
                    self.last_transaction = {'jan': jan_code, 'row': cell.row, 'log_data': log_data}
                    # 取り消しボタンを押せるようにする
                    self.cancel_button.config(state=tk.NORMAL)
                else: # 在庫が0の場合
                    self.result_text.set(f'{product_name}\nは在庫がありません！')
            else: # 商品マスタにJANコードが見つからなかった場合
                self.result_text.set('この商品は未登録です')

        except Exception as e: # 上記の処理中に予期せぬエラーが発生した場合
            self.result_text.set("エラーが発生しました")
            print(f"エラー詳細: {e}", file=sys.stderr) # エラー内容をターミナルに出力

        # 次のスキャンに備えて、入力欄を空にリセットする
        self.entry_text.set("")
        # 再度、非表示入力欄をアクティブにする（これが無いと次のスキャンを受け付けられない）
        self.hidden_entry.focus_set()

    def undo_last_transaction(self):
        """直前のスキャン操作を取り消す処理"""
        # 取り消すべき取引情報がない場合は何もしない
        if not self.last_transaction:
            self.result_text.set("取り消す操作がありません")
            return

        self.info_text.set(f"取り消し処理中...")
        self.update_idletasks()

        try:
            # 1. 在庫マスターの在庫を元に戻す
            jan_code = self.last_transaction['jan']
            sheet_row = self.last_transaction['row']
            current_stock = int(self.master_sheet.cell(sheet_row, 4).value)
            restored_stock = current_stock + 1 # 在庫を1増やす
            self.master_sheet.update_cell(sheet_row, 4, restored_stock)

            # 2. 購入履歴から該当ログを削除する
            # 安全のため、保存しておいたログデータと完全に一致する最後の行を探して削除します
            all_log_data = self.log_sheet.get_all_values()
            # シートの下から上に向かって探すことで、最新のログを確実に見つける
            for i in range(len(all_log_data) - 1, 0, -1):
                # Gspreadのappend_rowは値を文字列として保存することがあるため、比較用に文字列に変換
                log_to_check = [str(item) for item in self.last_transaction['log_data']]
                if all_log_data[i] == log_to_check:
                    # Gspreadの行番号は1から始まるので、リストのインデックス(i)に1を足す
                    self.log_sheet.delete_rows(i + 1)
                    break # 1件削除したらループを抜ける

            product_name = self.master_sheet.cell(sheet_row, 1).value
            self.result_text.set(f"{product_name}の購入を\n取り消しました (残り: {restored_stock}個)")

        except Exception as e:
            self.result_text.set("取り消し中にエラーが発生しました")
            print(f"取り消しエラー詳細: {e}", file=sys.stderr)

        finally:
            # 正常終了でもエラーでも、取り消し処理後はボタンを無効化し、状態をリセット
            self.last_transaction = None
            self.cancel_button.config(state=tk.DISABLED)
            self.info_text.set('商品のバーコードをスキャンしてください')

    def quit_app(self, event=None):
        """Escapeキーでアプリケーションを終了する"""
        self.destroy()


# ==============================================================================
# アプリケーションの実行ブロック
# ==============================================================================
# このファイルが直接実行された場合にのみ、以下のコードが実行される
if __name__ == "__main__":
    # Appクラスのインスタンスを作成
    app = App()
    # ウィンドウを表示し、イベントの待機ループを開始する
    app.mainloop()