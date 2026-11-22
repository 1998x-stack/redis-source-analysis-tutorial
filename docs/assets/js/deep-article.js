/* Independent, accessible mechanism explorers for chapters 06–10. */
(() => {
  "use strict";
  const cases = {
    "dict-progress": {
      start: "旧表 ht_table[0] 有有效桶；扩容分配 ht_table[1]，rehashidx 从 0 开始。查找要考虑待迁移条目，新插入将放入新表。",
      during: "rehashidx = 3 表示更早的旧桶已处理并清空。dictRehash 按桶搬迁整条碰撞链；旧表尚未清零时查找可能检查两张表。",
      done: "当 ht_used[0] 变为 0 时释放旧桶数组，以新表替换 ht_table[0]，把 rehashidx 重置为 -1；双表期结束。"
    },
    "object-encoding": {
      integer: "字符串内容是 42：如果 tryObjectEncoding 成功识别并满足表示条件，可能成为 OBJ_ENCODING_INT；此时 ptr 不应被当作 SDS 指针。",
      short: "20 字节的非整数文本：createStringObject() 首次创建时满足 44 字节阈值，通常使用 OBJ_ENCODING_EMBSTR，与 SDS 处于同一分配块。",
      long: "80 字节非整数文本：高于 44 字节的创建阈值，默认选择 RAW，对象和 SDS 分别管理。",
      mutable: "短字符串 APPEND 需要可变空间。EMBSTR 本身不适合原地 reallocate，Redis 可能先将值转为 RAW，再做 SDS 追加。"
    },
    "set-conditions": {
      "nx-miss": "NX + 键不存在：允许写入新值，默认返回 OK；SET 的值是一个 String 对象。",
      "nx-hit": "NX + 键已存在：条件失败，不改写旧值；未使用 GET 时返回 Null。",
      "xx-miss": "XX + 键不存在：条件失败，不创建新键；未使用 GET 时返回 Null。",
      "xx-hit": "XX + 键已存在：允许覆盖并返回 OK；如果不带 KEEPTTL 或显式过期参数，旧 TTL 通常被清除。",
      "get-hit": "GET + 键旧值存在：执行时返回旧值，同时更新键值；若旧值类型不是 String 则需要处理类型错误。",
      ttl: "SET 更新带 TTL 的键：默认替换值并删除之前的 TTL。KEEPTTL 明确要求保留原有效期。"
    },
    "block-phase": {
      available: "检查时已有非空 List：blockingPopGenericCommand 立即弹出，回复 [key,value]，无需注册 CLIENT_BLOCKED。",
      empty: "目标键都不能弹出：blockForKeys 为客户端记录等待键、过期时间和 BLOCKED_LIST 状态；事件循环继续运行。",
      signaled: "另一客户端写入：若有等待者，signalKeyAsReady 将该 key 去重加入 ready_keys 队列，而不是直接向全部等待客户端广播元素。",
      served: "handleClientsBlockedOnKeys 服务 ready key，尝试给同 key 的最早等待者弹出元素；成功后解除阻塞并推进后续命令。",
      timeout: "等待超时而仍无可读元素：回复 Null 并解除阻塞。BLPOP timeout=0 则代表无超时限制。"
    }
  };
  document.querySelectorAll("[data-deep-demo]").forEach(box => {
    const type = box.getAttribute("data-deep-demo");
    const select = box.querySelector("select");
    const output = box.querySelector("[data-output]");
    if (!select || !output) return;
    const update = () => {
      if (type === "skip-level") {
        const level = Number(select.value);
        const prob = Math.pow(0.25, level - 1) * 100;
        output.textContent = "单个节点高度 ≥ " + level + " 的理论概率约 " + prob.toLocaleString("zh-CN",{maximumFractionDigits:6}) + "%。这不决定具体节点高度，也不能据此直接预测总层数。";
      } else {
        output.textContent = cases[type]?.[select.value] ?? "暂无该状态说明";
      }
    };
    select.addEventListener("change", update);
    select.addEventListener("input", update);
    update();
  });
})();