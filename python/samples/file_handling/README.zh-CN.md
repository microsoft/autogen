# AutoGen 文件处理示例

此示例演示如何使用 AutoGen 处理文件内容。它利用了 AutoGen 的 `MultiModalMessage` 和 `File` 类，使代理能够处理文件并根据其内容回答问题。

## 前提条件

1.  **安装必要的库**：
    从 AutoGen 项目的根目录运行：
    ```bash
    pip install -e ".[all]"
    ```

2.  **OpenAI API 密钥**：
    确保您拥有一个有效的 OpenAI API 密钥。

3.  **配置文件**：
    在 `python/samples/file_handling/` 目录下创建一个名为 `config.json` 的配置文件。此文件应包含您的 API 密钥和您希望使用的模型（例如，支持文件处理的模型，如 `gpt-4o`）。

    `config.json` 示例：
    ```json
    {
        "model": "gpt-4o",
        "api_key": "您的OPENAI_API_密钥"
    }
    ```
    请将 `"您的OPENAI_API_密钥"` 替换为您的实际 OpenAI API 密钥。

4.  **示例文件**：
    将以下示例文件放置在 `python/samples/file_handling/` 目录下：
    *   `sample_document.pdf`：一个示例 PDF 文档。
    *   `sample_image.jpg` (或 `.png`, `.jpeg`)：一个示例图像文件。
    示例脚本 `file_example.py` 配置为查找这些文件。

## 运行示例

在您的终端中，导航到 `python/samples/file_handling/` 目录并运行：

```bash
python file_example.py
```

## 示例脚本概述 (`file_example.py`)

该脚本演示了向模型发送文件的不同方法：

1.  **直接文件内容**：
    文件内容（例如 PDF 的内容）直接在请求中发送。底层系统通常会处理 base64 编码。

2.  **文件 ID 引用**：
    首先将文件（例如 PDF）上传到 OpenAI 服务（或模型客户端支持的其他类似服务）以获取 `file_id`。然后在后续消息中使用此 `file_id` 引用文件。

3.  **图像和文件 (PDF) 组合**：
    演示发送一个 `MultiModalMessage`，其中包含：
    *   一个图像（作为直接内容发送）。
    *   一个 PDF 文档（在上传后通过其 `file_id` 引用，或根据 `main()` 中活动的示例作为直接内容发送）。

默认情况下，`file_example.py` 中的 `main()` 函数设置为运行组合图像和 PDF（PDF 使用 `file_id`）的示例。您可以取消注释 `main()` 中的其他示例以测试不同的场景。

您可以修改 `file_example.py` 脚本来试验不同的文件类型、提示和处理方法。 