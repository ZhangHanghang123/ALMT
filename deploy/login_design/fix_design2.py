import sys

config = "/etc/nginx/sites-enabled/almd"
with open(config, "r") as f:
    lines = f.readlines()

# 删除现有的 design location 块（89-94 行）
new_lines = []
skip_range = range(88, 95)  # 0-indexed: 88=line89, 94=line95
for i, line in enumerate(lines):
    if i in skip_range:
        continue
    new_lines.append(line)

# 在 server 块结尾的 "}" 前（第88行前，0-indexed）插入新的 design location
# 但先按 nginx 规则，location 顺序必须从最长前缀到最短前缀
# /almd/assets, /almd/, /almd/api/, /almt/..., /design/...
# 实际上问题不在顺序——而是嵌套检查：前缀 location 不能"跨越"其他前缀 location

# 真正的问题是 nginx 不允许在一个普通 location 内部又定义另一个普通 location（即使是 server-level 的并列 location），如果两个 location 有公共前缀
# 实际上 nginx 的要求是：所有非 named 的 location 必须在 server 级别按"前缀从最长到最短"排列

# 简单方案：把 design location 改名为 @design 别名，并用 internal + try_files 在前面引用
# 或者使用 rewrite + alias

# 最简方案：删除现有的，加在最前面（最长前缀 = 空字符串，但要有 ^~ 修饰 = 优先匹配）
# 实际上 ^~ 是修饰匹配优先级为前缀匹配（不计正则），位置不影响
# 真问题是嵌套判定：/design/ 和 /almt/api/ 不应该有公共前缀，但 nginx 报"outside location"说明有嵌套判定
# 实际上当一个 location 内部有 alias + try_files 时被认为有内部嵌套结构

# 尝试方案：把 location 块放到 /almd/api/ 等其他 location 之后的最末尾（即 server 块结束前），并改用 internal + rewrite
# 这里直接尝试一个最简形式

insert_text = """
    # ===== 设计预览 (login_design) =====
    location ^~ /design/ {
        alias /var/www/portal/;
        try_files $uri $uri/ =404;
    }
"""

# 找到 server 块最后一个 } 的位置
result = []
for i, line in enumerate(new_lines):
    result.append(line)
    # 在最后一个 } 之前
    if line.strip() == "}":
        # 检查是否是 server 的最后一行
        if i == len(new_lines) - 1:
            result.insert(-1, insert_text)

with open(config, "w") as f:
    f.writelines(result)

print("done")