# スーパーバイザー連携

## 概要

本システムは、動画作成依頼を受けたメインスーパーバイザーが、他のスーパーバイザーと連携してタスクを遂行するプロセスを自動化するものです。複数のスーパーバイザーが、単一の命令を実行するために、指揮命令可能なメンバーに対しルーティングと命令内容の生成を繰り返し行い、タスクを効率的に分担・実行します。

スーパーバイザー間で命令内容に関する不明点や達成困難な点が発生した場合は、理由を明記した上で命令元のスーパーバイザーへ問い合わせを行うことで、円滑な連携を実現します。

## 対応環境

* **Python:** 3.9, 3.10, 3.11, 3.12, 3.13

## 環境変数

本システムを実行するためには、以下の環境変数を設定する必要があります。

* `CustomSearchAPIAPIKEY`: Google Custom Search APIのAPIキー
* `SEARCH_ENGINE_ID`: Google Custom Searchの検索エンジンID
* `regionName_TOKYO`: (例: `AWS_REGION_TOKYO`) boto3を使用するリージョン名（東京リージョン）
* `regionName_US`: (例: `AWS_REGION_US_EAST_1`) boto3を使用するリージョン名（米国リージョン）

**boto3の設定について:**

本システムはAWS SDK for Python (boto3) を利用してAWSのサービスと連携します。環境変数 `AWS_ACCESS_KEY_ID`、`AWS_SECRET_ACCESS_KEY`、`regionName_TOKYO` および `regionName_US` が適切に設定されていることを確認してください。これらの認証情報は、AWSのIAMユーザーまたはインスタンスプロファイルを通じて提供される必要があります。

## 使い方 (準備)

1.  **Pythonのインストール:** 対応するPythonのバージョン（3.9～3.13）がインストールされていることを確認してください。
2.  **環境変数の設定:** 上記の必要な環境変数をシステムに設定してください。
    ```bash
    export CustomSearchAPIAPIKEY="YOUR_CUSTOM_SEARCH_API_KEY"
    export SEARCH_ENGINE_ID="YOUR_SEARCH_ENGINE_ID"
    export regionName_TOKYO="ap-northeast-1" # 例：東京リージョンの場合
    export regionName_US="us-east-1"       # 例：米国東部リージョンの場合
    # boto3の認証情報も必要に応じて設定
    # export AWS_ACCESS_KEY_ID="YOUR_AWS_ACCESS_KEY_ID"
    # export AWS_SECRET_ACCESS_KEY="YOUR_AWS_SECRET_ACCESS_KEY"
    ```
3.  **必要なライブラリのインストール:** 以下のライブラリがrequirements.txtなどに記述されている場合は、インストールしてください。特にboto3が必要となります。
    ```bash
    pip install -r requirements.txt # 例
    # または
    pip install boto3
    ```
4.  **AWSの設定:** boto3を利用するために必要なAWSの認証情報が正しく設定されていることを確認してください。

## システムの概要 (連携フロー)

1.  **動画作成依頼の受付:** メインスーパーバイザーが動画作成の依頼を受け付けます。
2.  **タスクの分割とルーティング:** メインスーパーバイザーは、依頼内容に基づきタスクを分割し、それぞれのタスクを担当する他のスーパーバイザーにルーティングします。
3.  **命令の生成と実行:** 各スーパーバイザーは、割り当てられたタスクを実行するために、指揮命令可能なメンバーに対して具体的な命令を生成し、実行を指示します。このプロセスは、単一の命令が完了するまで繰り返されます。
4.  **結果報告:** 命令が達成されたと判断した場合、各スーパーバイザーはメインスーパーバイザーにその結果を報告します。
5.  **問い合わせ対応:** 命令内容に不明な点や達成が困難な点がある場合、各スーパーバイザーは理由を明記した上で、命令元のスーパーバイザーへ問い合わせを行います。

## ライセンス





# Supervisor Collaboration System

## Overview

This system automates the process by which a main supervisor, upon receiving a video creation request, collaborates with other supervisors to execute tasks. Multiple supervisors repeatedly perform routing and generate instructions for their commandable members to accomplish a single directive, thereby efficiently distributing and executing tasks.

To ensure smooth collaboration, if any supervisor encounters unclear instructions or difficulties in achieving a directive, they will inquire with the originating supervisor, clearly stating the reason for the query.

## Supported Environments

* **Python:** 3.9, 3.10, 3.11, 3.12, 3.13

## Environment Variables

To run this system, you need to set the following environment variables:

* `CustomSearchAPIAPIKEY`: API key for Google Custom Search API
* `SEARCH_ENGINE_ID`: Search engine ID for Google Custom Search
* `regionName_TOKYO`: (e.g., `AWS_REGION_TOKYO`) AWS region name to be used with boto3 (Tokyo region)
* `regionName_US`: (e.g., `AWS_REGION_US_EAST_1`) AWS region name to be used with boto3 (US region)

**About boto3 Configuration:**

This system utilizes the AWS SDK for Python (boto3) to interact with AWS services. Ensure that the environment variables `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `regionName_TOKYO`, and `regionName_US` are configured correctly. These credentials should be provided through an AWS IAM user or an instance profile.

## Usage (Preparation)

1.  **Install Python:** Verify that a supported Python version (3.9 to 3.13) is installed.
2.  **Set Environment Variables:** Set the necessary environment variables in your system.
    ```bash
    export CustomSearchAPIAPIKEY="YOUR_CUSTOM_SEARCH_API_KEY"
    export SEARCH_ENGINE_ID="YOUR_SEARCH_ENGINE_ID"
    export regionName_TOKYO="ap-northeast-1" # Example: Tokyo region
    export regionName_US="us-east-1"       # Example: US East region
    # Configure boto3 credentials if necessary
    # export AWS_ACCESS_KEY_ID="YOUR_AWS_ACCESS_KEY_ID"
    # export AWS_SECRET_ACCESS_KEY="YOUR_AWS_SECRET_ACCESS_KEY"
    ```
3.  **Install Required Libraries:** If a `requirements.txt` file exists listing the dependencies, install them. Specifically, boto3 is required.
    ```bash
    pip install -r requirements.txt # Example
    # Or
    pip install boto3
    ```
4.  **Configure AWS:** Ensure that the necessary AWS credentials for boto3 are correctly configured.

## System Overview (Collaboration Flow)

1.  **Receiving Video Creation Request:** The main supervisor receives a request for video creation.
2.  **Task Division and Routing:** The main supervisor divides the request into tasks and routes each task to other responsible supervisors.
3.  **Instruction Generation and Execution:** Each supervisor generates specific instructions for their commandable members to execute the assigned task. This process is repeated until a single directive is accomplished.
4.  **Result Reporting:** Once a directive is deemed complete, each supervisor reports the result to the main supervisor.
5.  **Inquiry Handling:** If a supervisor has unclear instructions or faces difficulties in achieving a directive, they will inquire with the originating supervisor, clearly stating the reason.

## License

[Insert license information here. Example: MIT License]
