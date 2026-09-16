# CanDo 手动提交

1. 查看 `.report.json`：生成必须成功，结构验证为 PASS。
2. 用 cadnano 打开 `.full.json` 检查设计；修改后需要重新验证主文件并按原样重新压缩。
3. 用户自行打开 CanDo 提交页面，将 `.cando_compact.json` 上传。
4. 页面上的 lattice 必须与报告的 `lattice_type` 一致。其余参数以页面当前要求及用户选择为准。
5. 如页面需要姓名、单位、邮箱或账号，由用户提供；生成器不收集这些信息。
6. 等待 CanDo 返回计算结果；本地输出状态 `CANDO_INPUT_GENERATED` 不表示已提交或已计算。

full 和 compact 的区别仅是 JSON 文本排版。不要删除 scaffold、staple 或其他结构数据；不要把 V1 的旧 scaffold-stripped 文件当成 V2 输出。

本版默认不自动提交，不生成虚构的三维结果，不保证 CanDo 收敛。CanDo 返回的预测也不能证明 DNA 在实验中能成功折叠。
