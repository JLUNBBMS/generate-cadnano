# generate-cadnano — V3.0.0

生成 cadnano v2 格式的 DNA 折纸 JSON。V3 保留 V2 的 8 个模板，新增 9 个参数化入口。生成器通过 scadnano 导出，再检查拓扑、晶格位点和实际占用几何；失败不交付设计文件。

## 安装与使用

Python 3.10 或更高版本：

```sh
python -m pip install -r requirements.txt
python scripts/check_deps.py
python scripts/template_design.py closed_rectangular_box -o output/box
```

Skill 安装目录须让入口直接位于 `generate-cadnano/SKILL.md`，不要多套一层目录。V3 的 Skill 名仍为 `generate-cadnano`；更新时替换旧安装，避免同时加载同名版本。

## 构型目录

| 入口 | 构型与默认值 |
|---|---|
| rectangle | V2 矩形板；square，8 helices × 128 bp |
| square | V2 近正方形板；square，16 helices，约 118 bp |
| long_strip | V2 长条板；square，4 helices × 128 bp |
| planar_plate | V2 宽板；square，24 helices × 128 bp |
| 2_helix_bundle | V2 两螺旋束；honeycomb，210 bp |
| 4_helix_bundle | V2 四螺旋束；honeycomb，210 bp；开放邻接链 |
| 6_helix_bundle | V2 六螺旋束；honeycomb，210 bp；含接缝 |
| regular_tube | V2 方形开口管；square，每边 4，总共 16 helices，128 bp |
| parametric_tube | V3 统一管道入口；默认 square 近圆截面，24 条管壁螺旋，192 bp |
| square_tube | V3 方形管；square，宽/高计数各 3，共 12 条管壁螺旋，192 bp |
| rectangular_tube | V3 矩形管；square，宽/高计数 3/4，共 14 条管壁螺旋，192 bp |
| polygonal_tube | V3 晶格多边形管；默认 square 四边形，24 条管壁螺旋，192 bp |
| near_circular_tube | V3 近圆管；按指定管壁螺旋数搜索截面，默认 square，24 条，192 bp |
| capped_square_tube | V3 固定端盖方管；默认双端盖，总长 384 bp，盖厚包络各 128 bp |
| capped_rectangular_tube | V3 固定端盖矩形管；默认双端盖、宽/高计数 3/4，总长 384 bp |
| closed_rectangular_box | V3 固定封闭长方体；矩形管壁加上下两个填充端盖，默认尺寸同上 |
| n_helix_bundle | V3 可变螺旋数的紧凑束；默认 honeycomb，12 条，210 bp |

V2 的参数默认值和路由保持兼容。新管道的两端形式由 `--end-style open|one_cap|two_caps` 控制；capped 入口不接受 open，closed_rectangular_box 只接受 two_caps。n_helix_bundle 不支持端盖。

## 固定端盖到底是什么

V3 使用平行螺旋的体素式容器：外周长螺旋形成管壁；内部短螺旋填充底部/顶部；中间的内部螺旋区留空。双端盖的同一内部 helix 列有两个互不重叠的占用区间，它们经管壁接入同一条 scaffold。

这是一体式、有厚度的固定盖，不是六张薄板折叠成的盒子，也没有铰链。DNA 螺旋间仍有纳米尺度间隙，不能称为液密容器。

默认盖厚包络为 128 bp，约 43.52 nm；总长 384 bp，约 130.56 nm；中间空腔的轴向包络为 128 bp。端部会因交叉相位产生台阶，实际占用区间以报告为准。当前不能提供任意薄盖；最小 cap_length 为 96 bp，且不保证所有尺寸组合可解。

## V3 参数及限制

| 参数 | 含义与范围 |
|---|---|
| --num-helices | 管道：管壁螺旋数；螺旋束：全部螺旋数。端盖会额外增加内部 helix 列，报告分别计数 |
| --bases-per-helix | 轴向坐标包络，96–4096 bp；并非每条 helix 都完整占用该长度 |
| --width-helices / --height-helices | square 晶格矩形截面的边计数 w/h，2–32；总管壁数为 2(w+h) |
| --side-helices | V3 方形的简写：w=h；不能与 width/height 同时指定。V2 regular_tube 保留旧语义与范围 |
| --cross-section | parametric_tube 可选 square、rectangle、polygon、near_circular |
| --polygon-sides | polygon 截面的边数；当前支持 square/4 或 honeycomb/6 |
| --end-style | open：两端开口；one_cap：低坐标端有底；two_caps：上下固定封闭 |
| --cap-length | 每个盖的轴向包络，96–1024 bp，默认 128；仅带盖时可用 |
| --scaffold-length | 单条 scaffold 长度预算，默认 7249 nt；不等于分配了 M13 序列 |

边计数为避免角点重复使用的约定：w=3 的一条边包含两个角点时实际有 4 个 helix 中心。square_tube 要求 w=h；不同边长请用 rectangular_tube。指定 num_helices 和边计数时二者必须一致。

带盖结构必须至少剩下 96 bp 的空腔轴向包络。默认矩形双盖有 14 条管壁 helix、6 条内部 helix 列，总计 20 条；双盖不把同一列重复计为两条。盖厚和内部数量增加都会消耗 scaffold。

两种晶格都支持近圆截面和通用螺旋束。精确矩形只支持 square。规则 honeycomb 六边形壳的管壁数量为 6、18、30、42……；其他数量可尝试 near_circular。三角形、任意边数的直边管并未实现，程序明确拒绝，不会用方管冒充。

闭环要求偶数管壁螺旋，但偶数并不保证可解。近圆截面用有限搜索优化物理径向离散程度，并要求 (最大半径−最小半径)/平均半径不超过 0.5；这是较宽松的离散近似阈值，不是光滑圆柱保证。报告公开实际径向误差。

搜索有预算限制，找不到方案时只能说“本次搜索未找到”，不能证明数学上绝无方案。某些封盖截面的奇偶平衡不能满足单 scaffold 路径；如默认路由模型下 w=h=4 的双盖会拒绝。可调整尺寸，不能自动更改用户参数。

## 示例

```sh
# 原有四螺旋束
python scripts/template_design.py 4_helix_bundle -o output/bundle4

# 32 螺旋近圆开口管
python scripts/template_design.py near_circular_tube --num-helices 32 --lattice honeycomb -o output/round32

# 3/4 边计数的矩形开口管
python scripts/template_design.py rectangular_tube --width-helices 3 --height-helices 4 -o output/rect

# 有底、上方开放的方形容器
python scripts/template_design.py capped_square_tube --end-style one_cap -o output/cup

# 固定顶部和底部的长方体
python scripts/template_design.py closed_rectangular_box --width-helices 3 --height-helices 4 -o output/box

# 统一参数化入口生成同样的矩形双盖结构
python scripts/template_design.py parametric_tube --cross-section rectangle --end-style two_caps -o output/param_box

# 24 螺旋束，不限定为 24 螺旋管
python scripts/template_design.py n_helix_bundle --num-helices 24 -o output/bundle24

python scripts/template_design.py --catalog
```

使用已有名称会拒绝覆盖。参数错误、搜索无解、预算不足或验证失败都返回非零退出码。

## 交付文件

- `.full.json`：用 cadnano 打开和编辑的主文件。
- `.cando_compact.json`：所有解析后 JSON 字段与 full 完全一致，仅去掉空白。
- `.report.json`：拓扑与几何验证、坐标、精确占用区间、管壁/总螺旋数、盖厚、链长和交叉数量。

`CANDO_INPUT_GENERATED` 只表示本地检查和 compact 保真通过。用户自行提交 CanDo，参见 [提交指南](references/cando-submission-guide.md)。

## 验证和证据

```sh
python scripts/test_design.py
python scripts/test_v3.py
python scripts/template_design.py --validate output/box.full.json --lattice square

# 在独立安装 cadnano2 / PyQt6 的环境中：
python scripts/check_cadnano.py output/box.full.json --lattice square
```

检查包括真实晶格邻接、方向与交叉相位、引用互反、单条 scaffold、20–60 nt staples、每个连续结合域至少 8 nt、配对覆盖、精确多区间占用、实际端盖截面、空腔无堵塞，以及要求的管壁/盖面 staple 接触。每个交叉只按有向 3′ 连接计一次。

`--validate` 单独检查输入拓扑。构型专属几何检查在生成流程中结合设计参数执行；不能从任意 JSON 自动认定其原始设计意图。插入/删除、非空旧式 loop、自定义路由仍不支持。

可选安装 matplotlib 后，从导出的真实占用数据生成几何预览：

```sh
python -m pip install matplotlib
python scripts/preview_geometry.py output/box.full.json output/box.png
```

预览是未松弛的晶格占用图，不是 CanDo/oxDNA 预测。发布证据见 [VALIDATION.md](VALIDATION.md)。

## 科学边界与迁移

结构检查和 cadnano 原生载入可证明已测样本的数据、连接和晶格约束；不能保证物理上无缠结、CanDo 收敛、折叠后的准确三维形状或实验稳定性。生成器不分配序列，也不自动执行 CanDo。浙江大学项目的 24 螺旋管可以作为参数参考，不能声称复刻其未公开路由。

Python API 保留 V2 create_design() 参数位置，新参数为可选关键字。新增构型 occupied_intervals 是按 helix ID 保存的区间列表，支持双盖不连续占用；V2 模板保留原先单区间报告。geometry_validation 在 V3 成功结果中必须为 PASS。详情见 [CHANGELOG.md](CHANGELOG.md) 和 [几何规则](references/v3-geometry.md)。
