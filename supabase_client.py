"""CLI 共通の Supabase クライアント

RLS で匿名アクセスを禁止しているため、管理者アカウントでサインインしてから使う。
.env は Git 管理されているため、パスワードは保存せず実行時に入力する
(SUPABASE_PASSWORD / admin_password を環境変数か Git 管理外の .env.local で渡した場合はそれを使う)。
"""

import os
from getpass import getpass
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client

# 秘密情報は Git 管理外の .env.local に置く。既に設定済みの環境変数は上書きしない
load_dotenv(Path(__file__).with_name(".env.local"))
load_dotenv(Path(__file__).with_name(".env"))


def get_client() -> Client:
    client = create_client(
        os.environ.get("SUPABASE_URL"),
        os.environ.get("SUPABASE_KEY")
    )

    # .env.local では admin_mail / admin_password の名前でも書ける
    email = os.environ.get("SUPABASE_EMAIL") or os.environ.get("admin_mail") or input("管理者メールアドレス: ")
    password = os.environ.get("SUPABASE_PASSWORD") or os.environ.get("admin_password") or getpass("パスワード: ")
    client.auth.sign_in_with_password({"email": email, "password": password})
    return client
