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

限制：别名覆盖有限，未识别的改写可能澄清；跨主题复杂问题未支持；全文差异判冲突过于保守。没有生产权限管理/大库分页/网络搜索。API 权限、网络和模型 JSON 输出首轮已连通 API，其余用例状态见本轮记录。

## 2026-11-10 首轮真实验收

[真实报告](../examples/live-20261110-144836/REPORT.md)。clear 通过。conflict 读取 D01 后试图提前回答，证据检查拒绝该动作，下一次模型响应无效，流程中止。其余用例未执行。

本次修复向模型返回未读文档 ID，并在模型响应无法解析时仅重试一次。离线检查通过。保留首轮 clear 证据，补测 conflict、outside、paraphrase、followup 和 tool_failure。

## 2026-11-10 第二轮真实验收

[原始报告](../examples/live-20261110-150614/REPORT.md)。本轮 conflict 通过。模型在证据校验拦截提前回答后，补读 D02，最终引用 D01 的 30 天和 D02 的 15 天并请求确认。outside 的模型响应无法解析，判为失败。paraphrase、followup、tool_failure 未执行。clear 通过证据来自首轮。

第三轮补测前修改：给模型增加资料外问题的检索和拒答动作示例，记录响应解析失败的具体阶段。单个响应格式错误会保留失败记录并继续跑下一条。离线用例和模拟格式错误后的继续执行检查均已通过，真实补测待执行。

## 2026-11-10 第三轮真实验收

[原始报告](../examples/live-20261110-152533/REPORT.md)。outside、paraphrase、followup、tool_failure 四项全部通过。结合首轮 clear 和第二轮 conflict，六项必验均有通过证据。冲突 Trace 保留了模型收到未读文档提示后补读 D02 并列出冲突的过程。
