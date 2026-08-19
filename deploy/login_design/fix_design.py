import sys

config = "/etc/nginx/sites-enabled/almd"
with open(config, "r") as f:
    content = f.read()

# 把 /design/ 改为精确前缀 ^~
content = content.replace(
    "location /design/ {\n        alias /var/www/portal/;",
    "location ^~ /design/ {\n        alias /var/www/portal/;"
)

with open(config, "w") as f:
    f.write(content)

print("ok")