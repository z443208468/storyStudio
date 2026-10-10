# P2-01 私有产物摘要哈希

本清单仅用于绑定私有文件身份，不包含原稿/角色材料正文。除“公开哈希证据”外，列出的文件均在 `.gitignore` 覆盖的私有目录中。原 ZIP SHA256：`300A829C7524D620AB89177AFCF52C03DFFEA633392C632F69A943F798DAD3B2`；版本：`JUN-SINGLE-02.3`。

| SHA256 | Relative path |
|---|---|
| `D3A15ECB58D1ECB01CDB7B97054A274773B146ED46B10E72F05F8EA3117233CF` | `inputs/private/release/300a829c7524d620ab89177afcf52c03dffea633392c632f69a943f798dad3b2/Cangqi_Jun_Release_2_3/source_manifest.json` |
| `BCDF3318E6E4ABDB60209B1E48B9D9C3322F166D300962665FB9ABE435F1ACBC` | `inputs/private/release/300a829c7524d620ab89177afcf52c03dffea633392c632f69a943f798dad3b2/Cangqi_Jun_Release_2_3/source_index.json` |
| `53C4F9C4F79AED2537928BF5C350D8C253C5783C7CC5D29536C9AA259B689223` | `inputs/private/release/300a829c7524d620ab89177afcf52c03dffea633392c632f69a943f798dad3b2/Cangqi_Jun_Release_2_3/script/君天离第二幕_32场完整稿.md` |
| `A40C67B8D16C08A22CAF5C554509CB7B4ADC9A9F9C0C26ED2D974FE73DDDE391` | `workspace/cangqi/90_canon/canon.md` |
| `AC6947AEF5D5C8D18C9EDD24513DF31AD0FB04D7C846BD4EFD0B315F8C492F90` | `workspace/cangqi/90_canon/character_bible.md` |
| `3480594A50A3F4837E2CA462A436DE2D759CDCD295B122A27FC34A495AAD7ECB` | `workspace/cangqi/90_canon/world_bible.md` |
| `1D614FCD8EF1D4E21C977231C1A162E2FB21FCAB306A56E0F6BF737E9AAD4CFA` | `workspace/cangqi/90_canon/glossary.md` |
| `90F2ADAE7C26F985101EBBE263A90F8B4801247337FEADF98AF0AE51530322FA` | `workspace/cangqi/90_canon/timeline.md` |
| `16A911E38DAEB7232E37407E9DC32091135E1A508856FD7A1459B6503EC9507E` | `workspace/cangqi/92_style_engine/style_guide.md` |
| `A6A0BA95C32701E178E3817E1B5C7A13F6F56755D738CB0983C2D264F5B45CBA` | `workspace/cangqi/92_style_engine/character_voice_samples.md` |
| `4E22C8F3732D172808304A32FE8F2266EDDFE152D3A0FFED8F3184F9B0347395` | `workspace/cangqi/92_style_engine/forbidden_patterns.md` |

索引核对：32 个 scene ID 均有源脚本定位；按 source_index.json 中 `excerpt_hash_method`/J32 hash_content_end_line 对源行连接 LF 后核对，32/32 hash 匹配。J32 的 scene_manifest.source_end_line=1171 是末尾空行，私有派生索引保留其原值并另记有效 hash 内容终止行1170。未运行输入包程序。Canon/Style和source_index/source_manifest存放于忽略目录；原始源包仅作只读输入。
