# generate-cadnano — V2.0.0

根据固定模板生成 cadnano v2 DNA 折纸设计 JSON。生成器使用 `scadnano`；导出后检查实际 JSON 中的连接、坐标和 crossover 位点，全部通过才交付文件。

## 安装与快速使用

在此文件夹打开终端，使用 Python 3.10 或更高版本：

```sh
python -m pip install -r requirements.txt
python scripts/check_deps.py
python scripts/template_design.py 4_helix_bundle --bases-per-helix 210 -o output/bundle4
```

生成三个文件：

- `output/bundle4.full.json`：用 cadnano 打开、查看和编辑的主文件。
- `output/bundle4.cando_compact.json`：与主文件全部 JSON 内容一致、仅去掉排版空白的文件，供用户自行提交 CanDo。
- `output/bundle4.report.json`：版本、实际螺旋坐标、占用区间、长度、物理 crossover 数量和验证结果。

已有同名输出时拒绝覆盖，请换一个 `-o` 名称。参数错误、结构验证失败或未实现的形状均返回非零退出码；不会交付新的主文件或 compact 文件。输出目录名称由用户指定，没有固定的本机路径。

把此目录作为 Skill 安装后，也可以用自然语言描述需求。入口为 `SKILL.md`，代理应通过这里的命令或 `create_design()` 生成。

## 支持范围与参数

| 形状 | 默认晶格 | 默认参数 | 实际含义 |
|---|---|---|---|
| `rectangle` | square | 8 helices × 128 bp | 普通矩形板 |
| `square` | square | 16 helices；长度约 118 bp | 轴向/横向物理包络尺寸比 0.85–1.15 |
| `long_strip` | square | 4 helices × 128 bp | 轴向/横向包络尺寸比至少 3 |
| `planar_plate` | square | 24 helices × 128 bp | 横向宽度至少等于轴向长度的宽板 |
| `2_helix_bundle` | honeycomb | 2 helices × 210 bp | 两条相邻螺旋 |
| `4_helix_bundle` | honeycomb | 4 helices × 210 bp | 固定紧凑四螺旋截面；蜂窝排列是开放邻接链，并非四边闭环 |
| `6_helix_bundle` | honeycomb | 6 helices × 210 bp | 蜂窝六边形截面；含闭合接缝 staple crossover |
| `regular_tube` | square | 每边 4 helices × 128 bp | 方形周界，共 16 helices；含首尾接缝 staple crossover |

板状模板和螺旋束可以显式选择 `--lattice square` 或 `honeycomb`。蜂窝板的横截面是晶格决定的锯齿排列。方形管道只支持 square，选择 honeycomb 会报错，不会自动改回 square。square 晶格的六螺旋束采用固定 2×3 周界。

通用参数：

- `--bases-per-helix`：请求的轴向坐标包络长度，整数 96–4096 bp，**不是承诺每条螺旋都恰好占用这么多碱基**。
- `--num-helices`：板状模板为 2–64；2/4/6 螺旋束只能指定与名称相同的数值。管道请用 `--side-helices`。
- `--side-helices`：方形管道每边 1–16 个，总数为四倍。
- `--scaffold-length`：支架最大可用长度，默认 7249 nt；表示长度预算，不表示已分配 M13mp18 序列。
- `--catalog`：查看支持情况。

参数在范围内并不保证有可行的 staple 切口方案；不存在方案或超过 scaffold 长度预算时明确失败，需要调整尺寸。最小 96 bp 是模板计算范围，不是所有生物学结构的最小长度。

示例：

```sh
python scripts/template_design.py rectangle --num-helices 8 --bases-per-helix 128 -o output/plate
python scripts/template_design.py square --num-helices 16 -o output/square
python scripts/template_design.py long_strip --num-helices 4 --bases-per-helix 240 -o output/strip
python scripts/template_design.py regular_tube --side-helices 4 --bases-per-helix 128 -o output/tube
```

当前不生成：box、triangle、L/T/cross、挖孔板、框架、任意曲面、多模块组装等。V1 中仅部分实现或只列名称的 16 个模板已明确设为不支持。不会把其他形状冒充它们。

## 结构与尺寸约定

1. Scaffold 是一条连续线性链，依次穿过模板螺旋；每个跨螺旋连接都位于该方向的合法晶格位点。
2. Staples 使用合法完整交叉连接，再切分成 20–60 nt 的独立线性寡核苷酸；每个连续结合域至少 8 nt。**V1 的“每个域 20–60 nt”已替换：域长度与整条 staple 长度不同。** 这是本版本的设计约束，不能替代结合温度或实验筛选。
3. 交叉位点限制会使边缘略有台阶或缩进。报告列出每条 helix 的 `[start, end)` 占用区间、最大端部缩进、实际轴向跨度及估计包络尺寸。square 的尺寸比是请求包络的近似约束，并非光滑正方形保证。
4. JSON 的空白数组区间会补齐为晶格周期的整数倍；避免同时被 21 和 32 整除导致晶格推断歧义。填充区不计作占用碱基。
5. V2 不支持插入、删除（loop/skip）、非空旧式 loop 字段、单碱基孤立域或自定义路由。验证这些文件时明确失败，不会清除这些字段后假称验证通过。
6. 完整环状 scaffold 可由验证器检查；生成器只产生线性 scaffold。生成器不分配 DNA 序列。

## 验证与回归测试

```sh
python scripts/test_design.py
python scripts/template_design.py --validate output/bundle4.full.json --lattice honeycomb
```

本地检查包括：

- JSON 类型、必需字段、数组长度、整数连接记录、唯一 helix ID/坐标、编号与坐标的奇偶性。
- 以真实 `num` 建立映射；非连续编号和数组重新排序仍可正确验证。
- 前后连接互为反向引用；引用存在；同 helix 不越级；链的方向正确。
- 唯一连续 scaffold、长度预算、staple 分段和完整配对覆盖。
- 基于 `(row, col)` 的真实晶格邻接、方向相关 offset，以及交叉的左右端类型；scaffold/staple 都检查。
- 每条有向 3′ 跨螺旋连接只计一次；同时报告占用位置与寡核苷酸数量。
- 导出与生成器预期坐标/区间一致；full/compact 所有解析后字段完全一致。

可选的独立 cadnano 验证，在装有 `cadnano2`（PyQt6 版本）的独立环境中运行：

```sh
python scripts/check_cadnano.py output/bundle4.full.json --lattice honeycomb
```

此工具调用 cadnano 自身的 decoder、邻接与 crossover 表、encoder，比较重新导出后的连接数组，不使用生成器的规则表。支持的输出坐标避免触发 cadnano 的 SQ100 对话框。具体发布验证结果见 `VALIDATION.md`。

## CanDo 与状态含义

`CANDO_INPUT_GENERATED` 只表示本地结构检查通过并生成了保留全部拓扑的 compact 文件。它不是 CanDo 服务验收状态。

用户自行把 compact JSON 交给 CanDo，并选择报告中的 lattice。自动运行脚本不会上传或注册账号。参见 `references/cando-submission-guide.md`。

本版证明范围是连接、晶格约束、cadnano 原生载入与往返一致性；不能保证 CanDo 收敛、预测三维形状完全符合期望、实际折叠或实验稳定性。所有输出的序列状态均为 `not_assigned`，实验状态均为 `EXPERIMENTALLY_UNVALIDATED`。

## Python API 与 V1 迁移

```python
from template_design import create_design

result = create_design(
    shape_id="4_helix_bundle",
    output_basename="output/bundle4",
    bases_per_helix=210,
)
if result["design_status"] != "GENERATED":
    raise RuntimeError(result["error"])
```

从外部脚本导入时将 `scripts/` 加入 Python 模块搜索路径，或从该目录调用。`validation_report` 在 V2 是含 `status/errors/counts` 的统一对象。V1 的宽松验证函数和 scaffold-stripped `.cando.json` 生成接口已移除；验证统一使用 `validation.validate()` 或 CLI。V1 的自定义路由/循环插入等未实现承诺不再保留。变化详见 `CHANGELOG.md`。
