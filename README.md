# BugFetcherApp

参考repo：https://github.com/wdtools/BugFetcher.git

A multi-interface application for fetching bugs from ZenTao and sending notifications to Feishu.

## 计划的功能：
- 将schemas.yaml导入到Dify，通过工作流读取数据，并生成问题分析报告，并发送到飞书。
- 添加一个定时任务，每天定时发送邮件给管理员，提醒管理员检查是否有新的bug。
- 查询指定的bug，并进行分析，发送到飞书。
- 固定查询每月的bug书，并通过大模型进行处理分析，发送到飞书。

## Modes
- **CLI**: Command-line interface
- **GUI**: Tkinter-based graphical interface
- **API**: FastAPI-based RESTful API

## Installation
```bash
pip install -r requirements.txt
```

## 使用方法

- **CLI模式**:
``` bash
python main.py cli --url "http://zentao.example.com" --username "user" --password "pass" --interval 30
```
- **GUI模式**:
```bash
python main.py gui
```

- **API模式**:
```bash
python main.py api
```

