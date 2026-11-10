# 评估

实际执行：10 个 unittest 测试方法通过（含多场景子测试），9/9 离线验收通过。证据：[测试日志](../examples/test-results.txt)、[汇总及逐项输入/输出/断言链接](../examples/mock-validation/REPORT.md)。真实模型首轮已执行两个用例，见下方记录。

| 验收点 | 实际结果与 Trace |
|---|---|
| 明确答案 | [clear](../examples/mock-validation/clear/output.json)：引用 D01，30 天 |
| 文档冲突 | [conflict](../examples/mock-validation/conflict/output.json)：D01 30 天、D02 15 天，needs_confirmation |
| 资料外 | [outside](../examples/mock-validation/outside/output.json)：needs_information，无引用 |
| 改写相似问题 | [paraphrase](../examples/mock-validation/paraphrase/output.json)：垫付映射报销 |
| 上下文追问 | [followup](../examples/mock-validation/followup/output.json)：补充查询，不采纳历史助手 90 天说法 |
| 工具失败 | [tool_failure](../examples/mock-validation/tool_failure/output.json)、[read_failure](../examples/mock-validation/read_failure/output.json)：不伪造成功 |
| 瞬时失败恢复 | [transient_failure](../examples/mock-validation/transient_failure/output.json)：错误返回后重试 |
| 替换资料 | [replaced_document](../examples/mock-validation/replaced_document/output.json)：答案随 D01 改为 45 天 |

上述路径为实际执行 Mock 的记录，不是模型能力证据。真实验收执行 README 命令，重点比较 clear 与 conflict，以及 followup 的补查动作。明确引用应与相应用例 documents.json 逐字一致。

限制：别名覆盖有限，未识别的改写可能澄清；跨主题复杂问题未支持；全文差异判冲突过于保守。没有生产权限管理/大库分页/网络搜索。API 权限、网络和模型 JSON 输出首轮已连通 API，其余真实用例待补测。

## 2026-11-10 首轮真实验收

[真实报告](../examples/live-20261110-144836/REPORT.md)。clear 通过。conflict 读取 D01 后试图提前回答，证据检查拒绝该动作，下一次模型响应无效，流程中止。其余用例未执行。

本次修复向模型返回未读文档 ID，并在模型响应无法解析时仅重试一次。离线检查通过。保留首轮 clear 证据，补测 conflict、outside、paraphrase、followup 和 tool_failure。
