import type { KnowledgeDocument } from "./types";
export const knowledgeSamples: KnowledgeDocument[] = [
  {
    format: "coderecall.knowledge",
    version: 1,
    deck: {
      id: "example-cpp",
      title: "C++ · 基础与实践",
      description: "示例知识库：把概念与实际代码联系起来。",
    },
    items: [
      {
        id: "example-cpp-raii",
        title: "用自己的话解释 RAII",
        kind: "qa",
        prompt: "RAII 如何帮助管理资源？用一个作用域中的对象举例。",
        answer:
          "RAII 将资源的生命周期绑定到对象。对象构造时获得资源，析构时释放资源。\n\n例如 `std::lock_guard<std::mutex>` 在构造时加锁，在离开作用域、对象析构时解锁。这样即使提前返回或抛出异常，也能释放锁。",
        tags: ["资源管理", "RAII"],
      },
      {
        id: "example-cpp-practice",
        title: "完成一次资源管理练习",
        kind: "procedure",
        prompt:
          "编写一个小程序，用作用域验证析构函数的调用时机。先说出预期，再运行。",
        answer:
          "1. 定义一个在构造和析构时打印信息的类。\n2. 在嵌套作用域中创建实例。\n3. 观察退出内部作用域时的打印顺序。\n4. 加入提前 `return`，再次验证对象的销毁。\n\n验收：能解释每一条输出对应哪个对象的生命周期。",
        tags: ["动手练习"],
      },
    ],
  },
  {
    format: "coderecall.knowledge",
    version: 1,
    deck: {
      id: "example-english",
      title: "英语 · 主动表达",
      description: "示例知识库：从识别单词走向造句。",
    },
    items: [
      {
        id: "example-english-recall",
        title: "recall 的语境",
        kind: "cloze",
        prompt:
          "I can {{c1::recall}} the details clearly.\n\n填入表示“回想起”的动词。",
        answer:
          "**recall**：回想起、记起。\n\nI can recall the details clearly.\n我能清楚地回想起细节。",
        tags: ["词汇", "语境"],
      },
      {
        id: "example-english-output",
        title: "从输入到输出",
        kind: "procedure",
        prompt: "用今天学到的一个词，口头描述一件自己的真实经历。",
        answer:
          "1. 选择一个新词。\n2. 说出一句与自己相关的话。\n3. 检查词义与句子结构。\n4. 不看笔记，再完整复述一次。\n\n验收：能独立说出自然、完整的句子。",
        tags: ["口语", "实践"],
      },
    ],
  },
  {
    format: "coderecall.knowledge",
    version: 1,
    deck: {
      id: "example-blender",
      title: "Blender · 动画练习",
      description: "示例实践卡：用操作过程检验记忆。",
    },
    items: [
      {
        id: "example-blender-practice",
        title: "复做一个简单位移动画",
        kind: "procedure",
        prompt:
          "从空白场景开始，为一个物体制作从 A 点到 B 点的位移动画。完成后再展开验收清单。",
        answer:
          "- [ ] 确定起止帧与位置。\n- [ ] 为位置设置关键帧。\n- [ ] 播放并检查运动轨迹与速度。\n- [ ] 调整后保存工程。\n\n在笔记里记录自己的 Blender 版本、操作路径和卡住的位置，下次优先复做这些步骤。",
        tags: ["关键帧", "项目练习"],
      },
    ],
  },
  {
    format: "coderecall.knowledge",
    version: 1,
    deck: {
      id: "example-ue5",
      title: "UE5 · 游戏制作",
      description: "示例实践卡：把项目任务变成可重复的练习。",
    },
    items: [
      {
        id: "example-ue5-practice",
        title: "复做一个交互原型",
        kind: "procedure",
        prompt:
          "选择自己项目里的一个简单交互，在测试关卡中独立复做，不查看原实现。",
        answer:
          "1. 写下触发条件、玩家输入与可见反馈。\n2. 建立最小测试关卡。\n3. 实现并运行该交互。\n4. 验证重复触发与退出场景的行为。\n5. 与原实现对照，记录遗漏。\n\n验收：能够解释事件从触发到反馈的完整过程。",
        tags: ["交互", "项目练习"],
      },
    ],
  },
];
