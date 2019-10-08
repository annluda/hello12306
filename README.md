# hello12306 v0.1
登录 > 实时查询余票 > 提交订单 > 微信通知



### 说明
- 查询余票接口需要传入目的地出发地的代码，字典获取及转换在[station_names.py](py-files/station_names.py)
- 核心代码在web.py
- 验证码识别代码及模型[来源](https://github.com/zhaipro/easy12306), 成功率大概在100%！按照自己的习惯进行了重构。

### TODO
- 提交订单时的验证码识别
- cdn
- 预约抢票
- 查询订单状态（是否排队成功）
