/* Small progressive enhancements for chapters 11–15. All narrative survives without JS. */
(() => {
  "use strict";
  const lookup = {
    "set-operation": {
      inter: "SINTER：先按集合基数挑较小候选集合，遍历其中成员，对其余集合执行成员测试。候选基数和编码共同影响开销；结果是共有成员。",
      union: "SUNION：扫描所有输入集合并去重，复杂度至少受输入成员总量影响；输出集合需要真实存储唯一结果。",
      diff: "SDIFF：需要剔除出现在其他集合的成员，具体可能选取不同的扫描策略以减少比较。"
    },
    "stream-lifecycle": {
      new: "XADD：为 Stream 增加持有 ID 的记录，还没有产生消费组 Pending 状态。XLEN 计量原始流记录。",
      delivered: "XREADGROUP >：把新条目交付给消费者；通常把记录加入 group PEL 与 consumer PEL，指向同一 NACK 元信息（NOACK 是例外）。",
      acked: "XACK：移除 group/consumer Pending 状态并释放 NACK；它不等于 XDEL，也不直接减小 XLEN。",
      deleted: "XDEL 或 XTRIM：删除或裁剪原始 Stream 数据；对尚在 PEL 的 ID 仍可能需要按消费组语义处理。"
    },
    "event-order": {
      pre: "beforeSleep：处理待处理读、ready blocked keys、部分过期和 AOF/回复相关准备；可能影响是否进入阻塞 poll。",
      poll: "aeApiPoll：使用 epoll/kqueue/select 等后端等待 fd 就绪，超时预算受最早时间事件和 DONT_WAIT 约束。",
      fired: "文件事件：按 fd/mask 调用注册的 read/write callbacks；AE_BARRIER 可反转默认读先写顺序。",
      timer: "processTimeEvents：查找已到期时间事件执行回调，非 AE_NOMORE 返回值用于安排下一次时限。"
    },
    "io-model": {
      single: "io-threads=1：不创建额外网络 I/O 工作线程，读写通常在主线程处理。",
      write: "当线程启用且待写客户端数足够时，主线程分发回复写任务，工作线程调用 writeToClient，主线程等待全部完成。",
      read: "io-threads-do-reads=yes 允许读侧线程化；worker 可读取并解析部分请求，汇合后主线程继续处理待执行命令。",
      light: "I/O 待写客户端数量过低时，stopThreadedIOIfNeeded 可能停用额外线程、回退同步路径。"
    }
  };
  for (const box of document.querySelectorAll("[data-third-demo]")) {
    const kind = box.getAttribute("data-third-demo");
    const select = box.querySelector("select");
    const output = box.querySelector("[data-output]");
    if (!select || !output) continue;
    function update() {
      if (kind === "hll-precision") {
        const m = Number(select.value);
        output.textContent = "理论相对标准误差 1.04/√m：m = " + m + " 时约 " + (100 * 1.04 / Math.sqrt(m)).toFixed(3) + "%。Redis 7.2 实际采用 m=16384；概率误差不是对每次查询的误差上界。";
      } else if (kind === "cron-rate") {
        const hz = Number(select.value);
        output.textContent = "配置 hz = " + hz + "，理想基线间隔 1000/hz = " + (1000 / hz).toFixed(1) + " ms。dynamic-hz、单次回调耗时与事件循环调度都会使实际间隔变化。";
      } else {
        output.textContent = lookup[kind]?.[select.value] || "本状态暂无说明";
      }
    }
    select.addEventListener("change", update);
    select.addEventListener("input", update);
    update();
  }
})();