# 🍫 研究室 購買部在庫管理システム

## 1. 概要 (Overview)
このシステムは、Raspberry Piとバーコードリーダーを利用して、研究室のお菓子や備品の在庫をリアルタイムで管理するためのキオスク端末です。スキャンされた商品はGoogleスプレッドシートに自動で記録され、在庫管理の手間を大幅に削減することを目的としています。

## 2. 主な機能 (Features)
- **リアルタイム在庫連携:** Googleスプレッドシートを利用し、複数人での同時閲覧やリアルタイムな在庫確認が可能です。
- **バーコードによる簡単操作:** 商品のバーコードをスキャンするだけの直感的な操作で、在庫を減算します。
- **直前の操作の取り消し機能:** 万が一、間違った商品をスキャンしても、ボタン一つで直前の操作を元に戻せます。
- **キオスクモードでの自動起動:** Raspberry Piの電源を入れると、ネットワーク接続を待ってから自動で在庫管理アプリが起動します。

## 3. システム構成 (System Architecture)
- **入力端末:** Raspberry Pi (3.5インチモニター接続)
- **入力:** USBバーコードリーダー
- **データベース:** Google スプレッドシート
- **アプリケーション:** Python 3 + Tkinter (GUI)

## 4. セットアップ手順
このシステムをゼロからセットアップするための手順です。

### 4.1. Googleスプレッドシートの準備
1.  Googleドライブで新規にスプレッドシートを作成し、ファイル名を `購買部在庫管理システム` にします。
2.  ファイル内に、以下の構成と名前で2つのシートを**正確に**作成します。

 **シート1: `商品マスタ`**

| 列 | A | B | C | D | E | F | G |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **ヘッダー** | 商品名 | 分類 | 価格 | 在庫 | URL | JAN | 在庫金額 |

    
 **シート2: `購入履歴`**
| 列 | A | B | C | D | E |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **ヘッダー** | 購入日時 | JANコード | 商品名 | 数量 | 合計金額 |

### 4.2. Google APIの設定
1. Google Cloud Platformでプロジェクトを作成し、`Google Drive API`と`Google Sheets API`を有効化します。
2. サービスアカウントを作成し、キー（**JSONファイル**）をダウンロードします。
3. 上記で作成したスプレッドシートの「共有」設定で、JSONキーファイル内に記載の`client_email`のアドレスを**「編集者」**として追加します。

### 4.3. Raspberry Piへのファイル配置
1. ラズパイ上に、プロジェクト用のフォルダを作成します。（例: `~/okashi-kiosk`）
2. このフォルダに、以下の**4つのファイル**を配置します。

    - `main.py` （アプリケーション本体）
    - `start_kiosk.sh` （起動用スクリプト）
    - `your-credentials.json` （ステップ4.2で取得した認証キーファイル。実際のファイル名に合わせること）
    - `.gitignore` （Git管理用ファイル）

### 4.4. 依存ライブラリのインストール
ターミナルを開き、以下のコマンドでPythonライブラリをインストールします。
```bash
pip3 install gspread google-auth-oauthlib
```

### 4.5. 起動スクリプトの設定
1. `start_kiosk.sh` をテキストエディタで開き、**2箇所のパス**がご自身の環境と一致しているか確認・修正します。
    - `export KASHI_KIOSK_CREDS_PATH` の行： 認証JSONファイルの**フルパス**に修正。
    - `cd` の行： プロジェクトフォルダの**フルパス**に修正。
    ```sh
    #!/bin/bash

    # 接続が確立されるまで待機
    while ! ping -c 1 -W 1 google.com &> /dev/null; do
        echo "ネットワーク接続を待っています..."
        sleep 1
    done

    echo "ネットワーク接続完了。アプリケーションを起動します。"

    # 【重要】あなたのJSONキーファイルのフルパスに書き換えてください
    export KASHI_KIOSK_CREDS_PATH="/home/pi/okashi-kiosk/your-credentials.json"

    # main.pyが存在するディレクトリに移動してから実行
    cd /home/pi/okashi-kiosk/
    python3 main.py
    ```
    *(注: 上記パスは一例です。ご自身のユーザー名やフォルダ名に合わせてください)*

2. スクリプトに実行権限を付与します。
    ```bash
    chmod +x start_kiosk.sh
    ```

### 4.6. 自動起動（キオスク化）の設定
ラズパイの電源を入れたらアプリが自動で起動するように設定します。

1. `autostart`フォルダがなければ作成します。
    ```bash
    mkdir -p ~/.config/autostart
    ```
2. 自動起動設定ファイルを作成します。
    ```bash
    nano ~/.config/autostart/kiosk.desktop
    ```
3. エディタが開いたら、以下の内容を書き込み、`Exec=`のパスが`start_kiosk.sh`のフルパスと一致しているか確認して保存します。
    ```ini
    [Desktop Entry]
    Type=Application
    Name=KashiKiosk
    Exec=/home/pi/okashi-kiosk/start_kiosk.sh
    Terminal=false
    ```
    *(注: 上記パスは一例です。ご自身のユーザー名やフォルダ名に合わせてください)*

### 4.7. 再起動
ターミナルで `sudo reboot` を実行して再起動します。デスクトップ起動後、アプリが自動で立ち上がれば成功です。

## 5. 使い方
1. 商品のバーコードをスキャナにかざします。
2. 画面に結果が表示されるのを確認します。
3. 間違えた場合は、「直前の操作を取り消す」ボタンを押します。
4. 終了したい場合は、キーボードの`Esc`キーを押します。

# ありがとうございました