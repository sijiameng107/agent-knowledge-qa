# 项目 3：企业知识问答 Agent

Python 3.10+，仅标准库；本次使用 Python 3.14 执行。无需安装第三方依赖，无框架，无界面/部署要求。资料均为合成数据。

## 最快运行

在本项目目录执行：

```sh
python3 -m src.agent --mode mock --input data/request.json --output examples/demo.json
python3 -m unittest discover -s tests -v
python3 scripts/evaluate.py --mode mock --output examples/mock-validation
```

Mock 为脚本化测试替身，只证明流程和工程约束。当前离线验收 9/9，测试方法 10 项通过；真实模型首轮 clear 通过，conflict 未完成，详见评估文档。

## 智谱普通 API

```sh
zsh scripts/run_live.zsh
```

脚本隐藏输入密钥并仅在当前进程使用；也可预先 export ZHIPU_API_KEY。可用 ZHIPU_MODEL 指定账户支持的模型，默认 glm-4-flash-250414。API 失败会输出 HTTP 状态和脱敏错误，不会伪装成 Mock 成功。模型返回 JSON 动作，程序执行工具后将实际结果送回模型，直到结束或步数用尽。

结果保存 examples/live-时间/，每个用例包含输入、资料、实际输出及 Trace、断言结果。至少核对两条真实路径的后续动作是否随工具结果改变。没有 API 可用时保留离线入口并如实注明缺口。

## 评审入口

- [需求](docs/01-requirements.md)、[设计](docs/02-solution.md)
- [评估与限制](docs/03-evaluation.md)、[AI 辅助说明](docs/04-ai-usage.md)、[复盘](docs/05-retrospective.md)
- [离线实际结果](examples/mock-validation/REPORT.md)、[单元测试日志](examples/test-results.txt)
- 输入 data/request.json；资料 data/documents.json；核心 src/agent.py；模型接入 src/model.py。

Trace 的 decision_summary 为简短公开决策依据，不要求或存储模型内部思维链。每步保留参数、工具返回、后续动作和真实 API 响应元数据（live 时）。

## 提交状态

代码包可独立运行。正式考核仍要求题号、GitHub URL、最终 commit SHA；当前包不代表已经上传。完成真实验收后将证据与全部代码一起提交并取得最终 SHA。私有仓库需授予指定评审账号读取权限。无真实密钥或隐私数据。
