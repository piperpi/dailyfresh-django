===================
天天生鲜django项目
===================
概述
========
1. 生鲜类产品  B2C  PC电脑端网页
#. 功能模块：用户模块  商品模块（首页、 搜索、商品） 购物车模块  订单模块（下单、 支付）
#. 用户模块：注册、登录、激活、退出、个人中心、地址
#. 商品模块：首页、详情、列表、搜索（haystack+whoosh）
#. 购物车： 增加、删除、修改、查询
#. 订单模块：确认订单页面、提交订单（下单）、请求支付、查询支付结果、评论
#. django默认的认证系统 AbstractUser
#. itsdangerous  生成签名的token （序列化工具 dumps  loads）
#. 邮件 （django提供邮件支持 配置参数  send_mail）
#. celery (异步任务)
#. 页面静态化 （缓解压力  celery  nginx）
#. 缓存（缓解压力， 保存的位置、有效期、与数据库的一致性问题）
#. FastDFS (分布式的图片存储服务， 修改了django的默认文件存储系统)
#. 搜索（ whoosh  索引  分词）
#. 购物车redis 哈希 历史记录redis list
#. 高并发的库存问题 （mysql事务、悲观锁、乐观锁）
#. 支付宝的使用流程
#. nginx （负载均衡  提供静态文件）

项目初始化
================
复制所需文件下site-packages到python环境的site-packages

安装项目所需包
----------------

::

    pip install fdfs_client-py-master.zip
    pip install -r requirement.txt

修改 *setting.py* 文件
-------------------------
::

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',  # 数据库引擎
            'NAME': 'dailyfresh',  # 你要存储数据的库名，事先要创建之
            'USER': 'df_USER',  # 数据库用户名
            'PASSWORD': 'df_PW',  # 密码
            'HOST': '10.0.0.7',  # 主机
            'PORT': '3306',  # 数据库使用的端口
        }
    }

    # 发送邮件配置
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    # smpt服务地址
    EMAIL_HOST = 'smtp.163.com'
    EMAIL_PORT = 25
    # 发送邮件的邮箱
    EMAIL_HOST_USER = 'xxx@163.com'
    # 在邮箱中设置的客户端授权密码
    EMAIL_HOST_PASSWORD = 'xxx'
    # 收件人看到的发件人
    EMAIL_FROM = '天天生鲜<xxx@163.com>'

    # Django的缓存配置
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": "redis://:redis_PW@10.0.0.7:6379/1",
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            }
        }
    }

    # 设置fdfs存储服务器上nginx的IP和端口号
    FDFS_URL='http://10.0.0.7:8888/'

支付宝密钥
-------------
 **apps/order/alipay_public_key.pem** (公钥)

 **apps/order/app_private_key.pem** (私钥)

启动服务
---------

::

    systemctl start mariadb redis nginx
    cd /dailyfresh
    celery -A celery_tasks.tasks worker -l info

运行
------
::

    python manage.py makemigrations
    python manage.py migrate
    python manage.py rebuild_index
    python manage.py runserver

