import sys

config = "/etc/nginx/sites-enabled/almd"
with open(config, "r") as f:
    lines = f.readlines()

# 找到 server 块结束的 "}" 行
new_lines = []
inserted = False
for i, line in enumerate(lines):
    new_lines.append(line)
    # 在最后一个 "}" (server 块结尾) 前插入
    if not inserted and line.strip() == "}" and i == len(lines) - 1:
        new_lines.insert(-1, """
    # ===== 设计预览 (login_design) =====
    location /design/ {
        alias /var/www/portal/;
        index index.html;
        try_files $uri $uri/ =404;
    }
""")
        inserted = True

with open(config, "w") as f:
    f.writelines(new_lines)

print("done" if inserted else "FAIL")