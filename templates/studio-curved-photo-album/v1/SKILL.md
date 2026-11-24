---
name: studio-template-curved-photo-album
description: 立体照片翻页书，完整换稿，沿现有原生制作入口调用。
---

参考原帖：https://www.douyin.com/video/7677775651118152866。

保留：真实照片跨页编排→双面弯曲书页→翻页遮挡与投影→新图及新短句揭晓→最后一页收束。

换稿时必须重做：完整图片组与授权、逐页短句及顺序、裁切焦点、双面书页纹理、乐句和翻页时间。读取native/story.json及main.js；所有画面和时点来自新数据。pages数组指定合法照片、place、heading、lines；逐页检查照片主体裁切。双面书页的背面必须匹配下一跨页，不把平面切换说成立体翻页。更新project.json中全部changed_files哈希；经studio.py templates prepare→plan→workflow→授权make。审完整最终MP4的画面、声音、连续性与结尾，不以解码/文件存在代替审美。
