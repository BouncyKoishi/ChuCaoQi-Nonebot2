本目录存放已禁用的插件，仅作为备份保留，不会被 NoneBot2 加载。

禁用原因：当前仅使用 NapCat (OneBot V11) 单端运行，未接入官方 QQ Bot。

- auto_bind.py
  依赖双端同时在线，通过消息时间戳匹配实现 QQ <-> OpenId 自动绑定。
  无官方 QQ Bot 端时，该插件的所有事件处理器均无法触发，无实际作用。

- napcat_interceptor.py
  在双端运行时拦截 NapCat 端指令，防止同一指令被两端重复响应。
  仅 NapCat 单端运行时不存在重复响应问题，该拦截器无意义。

恢复方式：将插件文件移回 plugins/ 顶层目录，并重启 Bot 即可。
