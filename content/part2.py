"""原创题意、题解及可执行参考答案：二叉树、图、回溯与二分。"""


def problem(id, title, slug, difficulty, category, summary, params, returns,
            examples, method, python, cpp, approach, steps, correctness,
            time, space, constraints, pitfalls, **extra):
    return dict(id=id, title=title, slug=slug, difficulty=difficulty,
                category=category, summary=summary,
                params=[dict(name=n, type=t) for n, t in params], returns=returns,
                examples=[dict(input=i, output=o, explanation=e) for i, o, e in examples],
                method=method, python=python.strip(), cpp=cpp.strip(),
                approach=approach, steps=steps, correctness=correctness,
                time=time, space=space, constraints=constraints, pitfalls=pitfalls, **extra)


PROBLEMS = [
problem(94, '二叉树的中序遍历', 'binary-tree-inorder-traversal', '简单', '二叉树',
    '给定二叉树根节点 root，按左子树、当前节点、右子树的顺序返回全部节点值。输入树用层序数组表示，null 表示空节点。',
    [('root', 'TreeNode')], 'int[]',
    [([[1, None, 2, 3]], [1, 3, 2], '节点 3 是节点 2 的左孩子。'), ([[]], [], '空树没有可访问的节点。')],
    'inorderTraversal',
    '''class Solution:
    def inorderTraversal(self, root):
        result, stack = [], []
        node = root
        while node or stack:
            # 左链上的节点暂存，等待左子树处理完。
            while node:
                stack.append(node)
                node = node.left
            # 栈顶正是下一个应访问的节点。
            node = stack.pop()
            result.append(node.val)
            # 随后处理它的右子树。
            node = node.right
        return result''',
    '''class Solution {
public:
    vector<int> inorderTraversal(TreeNode* root) {
        vector<int> result;
        vector<TreeNode*> st;
        TreeNode* node = root;
        while (node || !st.empty()) {
            // 先把尚未访问的左链压栈。
            while (node) { st.push_back(node); node = node->left; }
            // 左子树已完成，可以访问当前节点。
            node = st.back(); st.pop_back();
            result.push_back(node->val);
            // 下一轮进入右子树。
            node = node->right;
        }
        return result;
    }
};''',
    '用显式栈模拟递归中序遍历；栈保存尚未访问的祖先。',
    ['沿左孩子连续入栈。', '弹出节点并记录值。', '转到右孩子，重复直到当前节点和栈都为空。'],
    '弹出一个节点时，其左子树已全部处理；右子树尚未开始。因此每个节点恰好在左右子树之间被访问，满足中序顺序。',
    'O(n)', 'O(h)，h 为树高；不计输出', ['0 ≤ 节点数 ≤ 100', '-100 ≤ 节点值 ≤ 100'],
    ['循环条件必须同时考虑当前节点和栈。', '转入右子树之前先记录当前值。']),

problem(104, '二叉树的最大深度', 'maximum-depth-of-binary-tree', '简单', '二叉树',
    '返回 root 到最远叶节点路径上的节点数。空树的深度为 0。', [('root', 'TreeNode')], 'int',
    [([[3, 9, 20, None, None, 15, 7]], 3, '到节点 15 或 7 的路径有 3 个节点。'), ([[]], 0, '空树深度为 0。')],
    'maxDepth',
    '''class Solution:
    def maxDepth(self, root):
        if not root:
            return 0
        # 用栈保存节点及其深度，避免退化长链触发递归限制。
        stack = [(root, 1)]
        deepest = 0
        while stack:
            node, depth = stack.pop()
            # 每个节点都可能刷新最大深度。
            deepest = max(deepest, depth)
            if node.left:
                stack.append((node.left, depth + 1))
            # 子节点比父节点深一层。
            if node.right:
                stack.append((node.right, depth + 1))
        return deepest''',
    '''class Solution {
public:
    int maxDepth(TreeNode* root) {
        if (!root) return 0;
        // 显式栈避免长链造成递归调用过深。
        vector<pair<TreeNode*, int>> st{{root, 1}};
        int deepest = 0;
        while (!st.empty()) {
            auto [node, depth] = st.back(); st.pop_back();
            // 更新已访问节点中的最大深度。
            deepest = max(deepest, depth);
            // 孩子节点的深度增加一。
            if (node->left) st.push_back({node->left, depth + 1});
            if (node->right) st.push_back({node->right, depth + 1});
        }
        return deepest;
    }
};''',
    '迭代深度优先遍历，每个栈项携带节点所在深度。',
    ['根节点以深度 1 入栈。', '弹出节点并更新最大深度。', '将存在的孩子连同深度加一后入栈。'],
    '根的深度正确；每次由父节点给孩子的深度加一，因此所有节点的深度均正确。遍历的最大值就是答案。',
    'O(n)', 'O(h)，h 为树高', ['0 ≤ 节点数 ≤ 10000', '-100 ≤ 节点值 ≤ 100'],
    ['深度按节点数计算，不是边数。', '空树应直接返回 0。']),

problem(226, '翻转二叉树', 'invert-binary-tree', '简单', '二叉树',
    '将二叉树每一个节点的左、右子树互换，原地修改树并返回根节点。', [('root', 'TreeNode')], 'TreeNode',
    [([[4, 2, 7, 1, 3, 6, 9]], [4, 7, 2, 9, 6, 3, 1], '所有节点的左右孩子互换。'), ([[]], [], '翻转空树仍是空树。')],
    'invertTree',
    '''class Solution:
    def invertTree(self, root):
        if not root:
            return None
        # 每个非空节点恰好加入栈一次。
        stack = [root]
        while stack:
            node = stack.pop()
            # 同时交换引用，不丢失原来的子树。
            node.left, node.right = node.right, node.left
            if node.left:
                stack.append(node.left)
            if node.right:
                stack.append(node.right)
        # 根节点本身没有改变。
        return root''',
    '''class Solution {
public:
    TreeNode* invertTree(TreeNode* root) {
        if (!root) return nullptr;
        // 栈中只保存非空节点。
        vector<TreeNode*> st{root};
        while (!st.empty()) {
            TreeNode* node = st.back(); st.pop_back();
            // 交换整个子树的指针。
            swap(node->left, node->right);
            if (node->left) st.push_back(node->left);
            if (node->right) st.push_back(node->right);
        }
        // 修改在原树上完成。
        return root;
    }
};''',
    '遍历所有节点并交换其左右孩子，使用显式栈控制遍历。',
    ['处理空树。', '逐个取出节点，交换左右指针。', '把两个非空孩子入栈。'],
    '镜像树要求每个节点左右关系反转。算法恰好交换所有节点的左右孩子一次，且不改变节点值或遗漏子树，因此得到整棵树的镜像。',
    'O(n)', 'O(h)，h 为树高', ['0 ≤ 节点数 ≤ 100', '-100 ≤ 节点值 ≤ 100'],
    ['交换的是节点引用而不是节点值。', '不要用覆盖赋值导致某一子树丢失。']),

problem(101, '对称二叉树', 'symmetric-tree', '简单', '二叉树',
    '判断一棵树是否关于根节点所在的竖直轴镜像对称。需要同时比较结构和节点值。', [('root', 'TreeNode')], 'bool',
    [([[1, 2, 2, 3, 4, 4, 3]], True, '两侧结构和值完全镜像。'), ([[1, 2, 2, None, 3, None, 3]], False, '两个值为 3 的节点都在右侧，不是镜像位置。')],
    'isSymmetric',
    '''class Solution:
    def isSymmetric(self, root):
        if not root:
            return True
        # 栈中每一对节点都应处于镜像位置。
        stack = [(root.left, root.right)]
        while stack:
            left, right = stack.pop()
            if not left and not right:
                continue
            # 只有一个为空或值不同，立即否定。
            if not left or not right or left.val != right.val:
                return False
            # 外侧与外侧、内侧与内侧配对。
            stack.append((left.left, right.right))
            stack.append((left.right, right.left))
        return True''',
    '''class Solution {
public:
    bool isSymmetric(TreeNode* root) {
        if (!root) return true;
        // 保存需要比较的镜像节点对。
        vector<pair<TreeNode*, TreeNode*>> st{{root->left, root->right}};
        while (!st.empty()) {
            auto [a, b] = st.back(); st.pop_back();
            if (!a && !b) continue;
            // 空节点位置也属于树的结构。
            if (!a || !b || a->val != b->val) return false;
            // 交叉比较孩子，保持镜像关系。
            st.push_back({a->left, b->right});
            st.push_back({a->right, b->left});
        }
        return true;
    }
};''',
    '成对遍历应当互为镜像的节点。',
    ['先比较根的左右子树。', '同时为空则继续；仅一个为空或值不等则失败。', '交叉加入两组孩子节点对。'],
    '镜像的充要条件是根值相等、左树的左孩子与右树的右孩子镜像、另一组孩子也镜像。算法逐层检查了这些条件。',
    'O(n)', 'O(h)，h 为树高', ['1 ≤ 节点数 ≤ 1000', '-100 ≤ 节点值 ≤ 100'],
    ['只比较每层数值是否回文会漏掉结构差异。', '孩子必须交叉配对。']),

problem(543, '二叉树的直径', 'diameter-of-binary-tree', '简单', '二叉树',
    '返回树中任意两个节点之间最长路径的边数。这条路径不一定经过根。', [('root', 'TreeNode')], 'int',
    [([[1, 2, 3, 4, 5]], 3, '从节点 4 经 2、1 到 3，共 3 条边。'), ([[1]], 0, '单节点之间没有边。')],
    'diameterOfBinaryTree',
    '''class Solution:
    def diameterOfBinaryTree(self, root):
        # 递归高度只在当前调用链上保存。
        import sys
        sys.setrecursionlimit(max(sys.getrecursionlimit(), 30000))
        diameter = 0
        def height(node):
            nonlocal diameter
            if not node:
                return 0
            left, right = height(node.left), height(node.right)
            # 两侧高度之和，正是经过当前节点的边数。
            diameter = max(diameter, left + right)
            # 向父节点只能贡献一条向下路径。
            return 1 + max(left, right)
        height(root)
        return diameter''',
    '''class Solution {
    int diameter = 0;
    int height(TreeNode* node) {
        if (!node) return 0;
        // 先计算左右子树的高度。
        int left = height(node->left), right = height(node->right);
        // 当前节点连接两条向下路径。
        diameter = max(diameter, left + right);
        // 给父节点返回较长的单侧路径。
        return 1 + max(left, right);
    }
public:
    int diameterOfBinaryTree(TreeNode* root) {
        diameter = 0;
        height(root);
        return diameter;
    }
};''',
    '后序遍历同时计算子树高度与经过当前节点的最长路径。',
    ['空节点高度为 0。', '用左右高度之和更新直径。', '向父节点返回较大高度加一。'],
    '任意路径都有一个最高节点。以该节点为转折时，最长路径取左右子树的最大向下深度。枚举所有转折节点即可覆盖全局最优路径。',
    'O(n)', 'O(h)，递归栈', ['1 ≤ 节点数 ≤ 10000', '-100 ≤ 节点值 ≤ 100'],
    ['高度以节点计数，而直径以边计数。', '必须在所有节点更新答案。']),

problem(102, '二叉树的层序遍历', 'binary-tree-level-order-traversal', '中等', '二叉树',
    '从上到下逐层访问二叉树，同一层从左到右。把每层节点值作为一个数组返回。', [('root', 'TreeNode')], 'int[][]',
    [([[3, 9, 20, None, None, 15, 7]], [[3], [9, 20], [15, 7]], '每个子数组对应一个深度。'), ([[]], [], '空树没有层。')],
    'levelOrder',
    '''from collections import deque

class Solution:
    def levelOrder(self, root):
        if not root:
            return []
        queue, result = deque([root]), []
        while queue:
            # 固定本层大小，新加入的孩子留到下一轮。
            level = []
            for _ in range(len(queue)):
                node = queue.popleft()
                level.append(node.val)
                # 左孩子先入队，维持从左到右的顺序。
                if node.left:
                    queue.append(node.left)
                if node.right:
                    queue.append(node.right)
            # 一层结束后保存独立数组。
            result.append(level)
        return result''',
    '''class Solution {
public:
    vector<vector<int>> levelOrder(TreeNode* root) {
        if (!root) return {};
        queue<TreeNode*> q;
        q.push(root);
        vector<vector<int>> result;
        while (!q.empty()) {
            // 仅处理进入本轮时已经在队列中的节点。
            int size = q.size();
            vector<int> level;
            for (int i = 0; i < size; ++i) {
                TreeNode* node = q.front(); q.pop();
                level.push_back(node->val);
                // 孩子按从左到右入队。
                if (node->left) q.push(node->left);
                if (node->right) q.push(node->right);
            }
            // 新加入的节点构成下一层。
            result.push_back(level);
        }
        return result;
    }
};''',
    '用队列进行广度优先搜索，在每轮开始时固定本层节点数量。',
    ['非空根入队。', '取队列当前大小，弹出这么多个节点并记录。', '按左右顺序加入孩子，保存本层答案。'],
    '初始队列仅含第一层。每轮恰好弹出整层并按顺序加入下一层，因此各轮输出分别是对应层的正确顺序。',
    'O(n)', 'O(w)，w 为最大层宽；不计输出', ['0 ≤ 节点数 ≤ 2000', '-1000 ≤ 节点值 ≤ 1000'],
    ['不要在循环过程中动态读取队列长度作为终点。', '空树返回空数组而不是 [[]]。']),

problem(108, '将有序数组转换为二叉搜索树', 'convert-sorted-array-to-binary-search-tree', '简单', '二叉树',
    '给定严格递增数组 nums，构造一棵包含全部元素的高度平衡二叉搜索树。任意节点的左右子树高度差至多为 1；可返回任意满足条件的树。',
    [('nums', 'int[]')], 'TreeNode',
    [([[-10, -3, 0, 5, 9]], [0, -10, 5, None, -3, None, 9], '每段选中点为根，得到一棵合法平衡搜索树。'), ([[1]], [1], '一个数形成一个根节点。')],
    'sortedArrayToBST',
    '''class Solution:
    def sortedArrayToBST(self, nums):
        def build(left, right):
            # 使用闭区间，空区间对应空子树。
            if left > right:
                return None
            mid = (left + right) // 2
            # 中点两侧的元素数量最多相差一个。
            node = TreeNode(nums[mid])
            node.left = build(left, mid - 1)
            node.right = build(mid + 1, right)
            # 用下标递归，避免切片复制。
            return node
        return build(0, len(nums) - 1)''',
    '''class Solution {
    TreeNode* build(vector<int>& nums, int left, int right) {
        // 闭区间为空时没有节点。
        if (left > right) return nullptr;
        int mid = left + (right - left) / 2;
        // 选择中点保证两侧规模均衡。
        TreeNode* node = new TreeNode(nums[mid]);
        node->left = build(nums, left, mid - 1);
        node->right = build(nums, mid + 1, right);
        // 所有元素恰好使用一次。
        return node;
    }
public:
    TreeNode* sortedArrayToBST(vector<int>& nums) {
        return build(nums, 0, static_cast<int>(nums.size()) - 1);
    }
};''',
    '每个有序区间选择中点作根，左右半段递归构造子树。',
    ['用左右下标表示待构造区间。', '中点元素成为根。', '分别构造两侧子树并连接。'],
    '有序数组保证左段所有数小于根、右段所有数大于根。中点划分使每层子问题规模接近，递归生成的两侧树高差至多一，所以同时满足搜索树与平衡要求。',
    'O(n)', 'O(log n)，递归栈；不计新建树', ['1 ≤ nums.length ≤ 10000', 'nums 严格递增'],
    ['使用数组下标而非反复复制切片。', '合法答案不唯一，不应只比固定树形。'], compare='bst'),

problem(98, '验证二叉搜索树', 'validate-binary-search-tree', '中等', '二叉树',
    '判断给定二叉树是否为严格二叉搜索树：每个节点左子树所有值更小，右子树所有值更大。重复值不允许。',
    [('root', 'TreeNode')], 'bool',
    [([[2, 1, 3]], True, '所有节点满足严格大小关系。'), ([[5, 1, 4, None, None, 3, 6]], False, '节点 4 位于根的右子树，却小于 5。')],
    'isValidBST',
    '''class Solution:
    def isValidBST(self, root):
        stack, node, previous = [], root, None
        while node or stack:
            # 中序顺序访问，正确搜索树应严格递增。
            while node:
                stack.append(node)
                node = node.left
            node = stack.pop()
            # None 表示尚未访问，不能用某个合法整数作哨兵。
            if previous is not None and node.val <= previous:
                return False
            previous = node.val
            # 接着验证右子树。
            node = node.right
        return True''',
    '''class Solution {
public:
    bool isValidBST(TreeNode* root) {
        vector<TreeNode*> st;
        TreeNode* node = root;
        long long previous = 0;
        bool hasPrevious = false;
        while (node || !st.empty()) {
            // 按中序依次访问节点。
            while (node) { st.push_back(node); node = node->left; }
            node = st.back(); st.pop_back();
            // 严格递增也排除了重复值。
            if (hasPrevious && node->val <= previous) return false;
            previous = node->val; hasPrevious = true;
            // 当前节点之后应访问右子树。
            node = node->right;
        }
        return true;
    }
};''',
    '利用严格二叉搜索树的中序遍历严格递增这一等价条件。',
    ['用栈进行中序遍历。', '将当前值与上一个访问值比较。', '出现不递增即失败，否则全程结束后成功。'],
    '搜索树的中序一定严格递增。反过来，若中序严格递增，则每个节点之前的左子树值均更小、之后的右子树值均更大，故所有节点满足搜索树定义。',
    'O(n)', 'O(h)，h 为树高', ['1 ≤ 节点数 ≤ 10000', '节点值在 32 位有符号整数范围内'],
    ['只检查直接孩子大小不足以验证整个子树。', '相等也必须判为非法。']),

problem(230, '二叉搜索树中第 K 小的元素', 'kth-smallest-element-in-a-bst', '中等', '二叉树',
    '给定二叉搜索树和有效正整数 k，返回按从小到大排列后位于第 k 位的节点值，计数从 1 开始。',
    [('root', 'TreeNode'), ('k', 'int')], 'int',
    [([[3, 1, 4, None, 2], 1], 1, '最小值是 1。'), ([[5, 3, 6, 2, 4, None, None, 1], 3], 3, '从小到大第三个值是 3。')],
    'kthSmallest',
    '''class Solution:
    def kthSmallest(self, root, k):
        stack, node = [], root
        while node or stack:
            # 中序遍历从最小值开始。
            while node:
                stack.append(node)
                node = node.left
            node = stack.pop()
            # 每访问一个节点，就消耗一个名额。
            k -= 1
            if k == 0:
                return node.val
            # 找到答案后立即返回，无需遍历整棵树。
            node = node.right''',
    '''class Solution {
public:
    int kthSmallest(TreeNode* root, int k) {
        vector<TreeNode*> st;
        TreeNode* node = root;
        while (node || !st.empty()) {
            // 中序访问对应升序顺序。
            while (node) { st.push_back(node); node = node->left; }
            node = st.back(); st.pop_back();
            // 第 k 次弹出的节点就是答案。
            if (--k == 0) return node->val;
            // 只遍历尚有必要访问的右子树。
            node = node->right;
        }
        return 0; // 题目保证 k 有效，不会到达这里。
    }
};''',
    '用中序遍历按升序取值，在访问到第 k 个节点时提前结束。',
    ['沿左链入栈。', '弹出节点并将 k 减一。', 'k 归零时返回，否则继续右子树。'],
    '搜索树中序顺序等于数值升序，所以第 k 个被访问的节点正是所求。提前结束不会影响已经确定的排名。',
    'O(h + k)，最坏 O(n)', 'O(h)', ['1 ≤ k ≤ 节点数 ≤ 10000', '给定的树是二叉搜索树'],
    ['k 从 1 开始计数。', '不要把入栈次数当作访问次数。']),

problem(199, '二叉树的右视图', 'binary-tree-right-side-view', '中等', '二叉树',
    '从二叉树右侧观察，返回每一层最右边节点的值，按从上到下排列。', [('root', 'TreeNode')], 'int[]',
    [([[1, 2, 3, None, 5, None, 4]], [1, 3, 4], '每层最右侧分别是 1、3、4。'), ([[1, 2]], [1, 2], '即使没有右孩子，左孩子也可能可见。')],
    'rightSideView',
    '''class Solution:
    def rightSideView(self, root):
        if not root:
            return []
        result, stack = [], [(root, 0)]
        while stack:
            node, depth = stack.pop()
            # 同深度首次访问的节点一定最靠右。
            if depth == len(result):
                result.append(node.val)
            # 栈后进先出，因此先压左孩子。
            if node.left:
                stack.append((node.left, depth + 1))
            # 右孩子会先于左孩子被访问。
            if node.right:
                stack.append((node.right, depth + 1))
        return result''',
    '''class Solution {
public:
    vector<int> rightSideView(TreeNode* root) {
        if (!root) return {};
        vector<int> result;
        vector<pair<TreeNode*, int>> st{{root, 0}};
        while (!st.empty()) {
            auto [node, depth] = st.back(); st.pop_back();
            // 每层只保留第一个访问到的节点。
            if (depth == static_cast<int>(result.size())) result.push_back(node->val);
            // 先压左，保证右子树优先弹出。
            if (node->left) st.push_back({node->left, depth + 1});
            // 按根、右、左顺序遍历。
            if (node->right) st.push_back({node->right, depth + 1});
        }
        return result;
    }
};''',
    '执行右子树优先的深度优先遍历，每个深度仅记录首次出现的节点。',
    ['把根及深度 0 入栈。', '首次到达某个深度时保存值。', '先压左孩子再压右孩子，让右侧先处理。'],
    '在同一层，位于更右的分支总是先被右优先遍历访问。因此该深度的首个节点就是从右侧可见的节点。',
    'O(n)', 'O(h)，不计输出', ['0 ≤ 节点数 ≤ 100', '-100 ≤ 节点值 ≤ 100'],
    ['右视图并不等于不断沿右孩子走。', '显式栈的入栈顺序与访问顺序相反。']),

problem(114, '二叉树展开为链表', 'flatten-binary-tree-to-linked-list', '中等', '二叉树',
    '原地把二叉树改为沿 right 指针连接的单链。顺序必须与原树的前序遍历一致，所有 left 指针设为空。函数无需返回值，展示修改后的树。',
    [('root', 'TreeNode')], 'void',
    [([[1, 2, 5, 3, 4, None, 6]], [1, None, 2, None, 3, None, 4, None, 5, None, 6], '展开顺序为 1、2、3、4、5、6。'), ([[]], [], '空树无需修改。')],
    'flatten',
    '''class Solution:
    def flatten(self, root):
        current = root
        while current:
            if current.left:
                # 左子树右链的末端可承接原来的右子树。
                predecessor = current.left
                while predecessor.right:
                    predecessor = predecessor.right
                predecessor.right = current.right
                # 左子树整体挪到右边，前序顺序保持不变。
                current.right = current.left
                current.left = None
            # 当前节点已就位，继续处理后继。
            current = current.right''',
    '''class Solution {
public:
    void flatten(TreeNode* root) {
        TreeNode* current = root;
        while (current) {
            if (current->left) {
                // 找到左子树最右路径的末端。
                TreeNode* predecessor = current->left;
                while (predecessor->right) predecessor = predecessor->right;
                // 原右子树接到左子树之后。
                predecessor->right = current->right;
                current->right = current->left;
                current->left = nullptr;
            }
            // 已处理前缀只通过右指针连接。
            current = current->right;
        }
    }
};''',
    '在当前节点处把左子树放到右侧，并将原右子树接到左子树右链末端。不断沿右指针前进。',
    ['若左子树存在，找到它最右路径的末端。', '将原右子树接在末端，再把左子树挪到右边并清空 left。', '向右移动，处理下一节点。'],
    '前序要求根之后依次是左子树、右子树。接线后左子树仍保留内部访问顺序，原右子树位于它之后。逐节点重复使已处理前缀固定且不丢失后续节点。',
    'O(n)，寻找前驱的右边总计线性', 'O(1)', ['0 ≤ 节点数 ≤ 2000', '-100 ≤ 节点值 ≤ 100'],
    ['必须先保存或接好原右子树，再覆盖 right。', '处理后每个 left 必须为空。'], mutates=0),

problem(105, '从前序与中序遍历序列构造二叉树', 'construct-binary-tree-from-preorder-and-inorder-traversal', '中等', '二叉树',
    '给定同一棵树的前序数组 preorder 和中序数组 inorder，重建并返回该树。节点值互不重复，输入保证有效。',
    [('preorder', 'int[]'), ('inorder', 'int[]')], 'TreeNode',
    [([[3, 9, 20, 15, 7], [9, 3, 15, 20, 7]], [3, 9, 20, None, None, 15, 7], '前序首值 3 是根，中序由此分成左右部分。'), ([[-1], [-1]], [-1], '单元素对应单节点树。')],
    'buildTree',
    '''class Solution:
    def buildTree(self, preorder, inorder):
        import sys
        sys.setrecursionlimit(max(sys.getrecursionlimit(), 10000))
        # 哈希表避免在每个递归中线性查找根。
        position = {value: i for i, value in enumerate(inorder)}
        next_root = 0
        def build(left, right):
            nonlocal next_root
            if left > right:
                return None
            value = preorder[next_root]
            next_root += 1
            node = TreeNode(value)
            middle = position[value]
            # 前序按根、左、右排列，递归顺序不能交换。
            node.left = build(left, middle - 1)
            node.right = build(middle + 1, right)
            return node
        # 传下标区间，不创建数组切片。
        return build(0, len(inorder) - 1)''',
    '''class Solution {
    unordered_map<int, int> position;
    int nextRoot = 0;
    TreeNode* build(vector<int>& preorder, int left, int right) {
        if (left > right) return nullptr;
        // 前序中尚未使用的首元素就是当前根。
        int value = preorder[nextRoot++];
        TreeNode* node = new TreeNode(value);
        int middle = position[value];
        // 中序根位置划分左右子树。
        node->left = build(preorder, left, middle - 1);
        node->right = build(preorder, middle + 1, right);
        return node;
    }
public:
    TreeNode* buildTree(vector<int>& preorder, vector<int>& inorder) {
        position.clear(); nextRoot = 0;
        // 预建索引，使每次定位根为平均常数时间。
        for (int i = 0; i < static_cast<int>(inorder.size()); ++i) position[inorder[i]] = i;
        return build(preorder, 0, static_cast<int>(inorder.size()) - 1);
    }
};''',
    '前序提供当前根，中序根位置划分左右子树；用哈希表加速定位。',
    ['记录每个值在中序中的下标。', '依次读取前序作为根。', '根据中序位置先递归构造左树，再构造右树。'],
    '前序首元素唯一确定根，中序中根两侧唯一确定左右节点集合。递归用相同规则重建两个子树，归纳可得整棵树与原树相同。',
    'O(n)，哈希平均复杂度', 'O(n)，索引表与递归栈；不计新建树', ['1 ≤ 数组长度 ≤ 3000', '两个数组长度相同、值互异，且是有效遍历结果'],
    ['必须先构造左子树，才能继续顺序消费前序。', '切片和反复 index 查找会退化到平方复杂度。']),

problem(437, '路径总和 III', 'path-sum-iii', '中等', '二叉树',
    '统计二叉树中节点值之和等于 targetSum 的向下路径数量。路径可从任意节点开始并在任意后代结束，但必须沿父到子的方向连续行进。',
    [('root', 'TreeNode'), ('targetSum', 'int')], 'int',
    [([[10, 5, -3, 3, 2, None, 11, 3, -2, None, 1], 8], 3, '合法路径为 5→3、5→2→1、-3→11。'), ([[0, 0, 0], 0], 5, '三个单节点路径和两条父子路径均符合。')],
    'pathSum',
    '''class Solution:
    def pathSum(self, root, targetSum):
        import sys
        sys.setrecursionlimit(max(sys.getrecursionlimit(), 5000))
        # 虚拟起点的前缀和为 0，允许路径从根开始。
        counts = {0: 1}
        def visit(node, prefix):
            if not node:
                return 0
            prefix += node.val
            total = counts.get(prefix - targetSum, 0)
            # 表中只保留当前祖先链上的前缀。
            counts[prefix] = counts.get(prefix, 0) + 1
            total += visit(node.left, prefix) + visit(node.right, prefix)
            # 回溯撤销，避免兄弟子树互相组合。
            counts[prefix] -= 1
            if counts[prefix] == 0:
                del counts[prefix]
            return total
        return visit(root, 0)''',
    '''class Solution {
    unordered_map<long long, int> counts;
    int visit(TreeNode* node, long long prefix, long long target) {
        if (!node) return 0;
        prefix += node->val;
        // 匹配祖先前缀即可确定以当前节点结尾的路径。
        auto found = counts.find(prefix - target);
        int total = found == counts.end() ? 0 : found->second;
        ++counts[prefix];
        total += visit(node->left, prefix, target) + visit(node->right, prefix, target);
        // 离开当前节点，撤销它在祖先链中的记录。
        if (--counts[prefix] == 0) counts.erase(prefix);
        return total;
    }
public:
    int pathSum(TreeNode* root, int targetSum) {
        counts.clear();
        // 根之前的空前缀使根起点路径也被统计。
        counts[0] = 1;
        return visit(root, 0, targetSum);
    }
};''',
    '维护当前根到节点路径的前缀和频次。两个前缀和之差等于目标，就构成一条合法向下路径。',
    ['先放入空前缀 0。', '到达节点后查询 prefix-targetSum 的出现次数。', '加入当前前缀，递归子树，再撤销。'],
    '以当前节点结尾的任意合法路径，都唯一对应一个祖先之前的前缀和。频次表恰含这条祖先链上的前缀，所以查询既不会漏计，也不会把不连续路径算入。',
    'O(n)，哈希平均复杂度', 'O(h)，h 为树高', ['0 ≤ 节点数 ≤ 1000', '-10^9 ≤ 节点值 ≤ 10^9', '-1000 ≤ targetSum ≤ 1000'],
    ['前缀和可能超出 32 位，C++ 使用 long long。', '离开子树时必须撤销频次。']),

problem(236, '二叉树的最近公共祖先', 'lowest-common-ancestor-of-a-binary-tree', '中等', '二叉树',
    '给定二叉树和其中两个不同节点 p、q，返回同时包含两者的最深祖先。节点可以是自己的祖先。输入中 p、q 用唯一节点值标识，输出祖先的值。',
    [('root', 'TreeNode'), ('p', 'TreeNode'), ('q', 'TreeNode')], 'TreeNode',
    [([[3, 5, 1, 6, 2, 0, 8, None, None, 7, 4], 5, 1], 3, '两个目标分属根的两棵子树。'), ([[3, 5, 1, 6, 2, 0, 8, None, None, 7, 4], 5, 4], 5, '节点 5 本身也是节点 4 的祖先。')],
    'lowestCommonAncestor',
    '''class Solution:
    def lowestCommonAncestor(self, root, p, q):
        import sys
        sys.setrecursionlimit(max(sys.getrecursionlimit(), 200000))
        def find(node):
            # 遇到目标直接上报它，节点也可成为自己的祖先。
            if not node or node is p or node is q:
                return node
            left, right = find(node.left), find(node.right)
            # 两侧均有结果，当前节点就是两条路径的交点。
            if left and right:
                return node
            # 仅一侧有结果时，把它继续向上传递。
            return left if left else right
        return find(root)''',
    '''class Solution {
public:
    TreeNode* lowestCommonAncestor(TreeNode* root, TreeNode* p, TreeNode* q) {
        // 空节点或目标节点是递归边界。
        if (!root || root == p || root == q) return root;
        TreeNode* left = lowestCommonAncestor(root->left, p, q);
        TreeNode* right = lowestCommonAncestor(root->right, p, q);
        // 两边分别找到目标，当前根就是最近交汇点。
        if (left && right) return root;
        // 把唯一的非空结果向父节点传递。
        return left ? left : right;
    }
};''',
    '后序搜索，把发现的目标或已确定的祖先向上传递。左右两侧同时返回结果时确定最近公共祖先。',
    ['为空或遇到 p、q 时直接返回。', '分别搜索两棵子树。', '两侧都非空返回当前节点，否则返回唯一非空结果。'],
    '若目标分居两侧，当前节点是最低的共同包含点；若在同侧，最近祖先由该侧递归确定；若当前即目标，则它是另一后代目标的祖先。输入保证两目标存在，因此最终返回正确节点。',
    'O(n)', 'O(h)，递归栈', ['2 ≤ 节点数 ≤ 100000', '节点值互不相同；p、q 存在且不同'],
    ['普通二叉树没有搜索树的大小关系。', '比较节点身份，不能随意创建同值节点替代输入目标。'], special='lca'),

problem(124, '二叉树中的最大路径和', 'binary-tree-maximum-path-sum', '困难', '二叉树',
    '在二叉树中选取一条非空简单路径，使经过节点的数值之和最大。路径可从任意节点开始和结束，每个节点最多出现一次。',
    [('root', 'TreeNode')], 'int',
    [([[-10, 9, 20, None, None, 15, 7]], 42, '路径 15→20→7 的和为 42。'), ([[-3]], -3, '路径必须非空，全负值时也要选择节点。')],
    'maxPathSum',
    '''class Solution:
    def maxPathSum(self, root):
        import sys
        sys.setrecursionlimit(max(sys.getrecursionlimit(), 70000))
        best = float('-inf')
        def gain(node):
            nonlocal best
            if not node:
                return 0
            # 负贡献不选，等价于不延伸到对应子树。
            left = max(0, gain(node.left))
            right = max(0, gain(node.right))
            # 作为路径最高点时可以同时连接左右两侧。
            best = max(best, node.val + left + right)
            # 交给父节点的路径只能选择一侧。
            return node.val + max(left, right)
        gain(root)
        return best''',
    '''class Solution {
    int best;
    int gain(TreeNode* node) {
        if (!node) return 0;
        // 不采用负数贡献，避免使路径和变小。
        int left = max(0, gain(node->left));
        int right = max(0, gain(node->right));
        // 以当前节点为最高点的完整候选路径。
        best = max(best, node->val + left + right);
        // 向上延伸时只能保留一个分支。
        return node->val + max(left, right);
    }
public:
    int maxPathSum(TreeNode* root) {
        best = INT_MIN;
        gain(root);
        return best;
    }
};''',
    '后序计算每个节点可向父节点提供的最大单侧贡献，同时用两侧贡献更新完整路径答案。',
    ['空节点贡献为 0，负贡献截断为 0。', '用节点值加左右贡献更新全局最大值。', '返回节点值加较大单侧贡献。'],
    '任何简单路径都有唯一最高节点。在该点可以连接左右两条向下路径；每侧取最大正贡献最优。遍历所有最高点覆盖全部路径，而返回单侧保证向上连接时不分叉。',
    'O(n)', 'O(h)，递归栈', ['1 ≤ 节点数 ≤ 30000', '-1000 ≤ 节点值 ≤ 1000'],
    ['全局答案不能初始化为 0，因为所有值可能为负。', '递归返回值不能同时包含左右分支。']),

problem(200, '岛屿数量', 'number-of-islands', '中等', '图论',
    '字符网格中 "1" 是陆地，"0" 是水。上下左右相邻的陆地属于同一座岛，斜对角不相连。统计岛屿数量；允许修改输入网格。',
    [('grid', 'char[][]')], 'int',
    [([[['1', '1', '0'], ['0', '1', '0'], ['1', '0', '1']]], 3, '右下和左下陆地各成一座岛。'), ([[['0', '0']]], 0, '没有陆地。')],
    'numIslands',
    '''class Solution:
    def numIslands(self, grid):
        rows, cols = len(grid), len(grid[0])
        islands = 0
        for r in range(rows):
            for c in range(cols):
                if grid[r][c] != '1':
                    continue
                islands += 1
                # 入栈时立刻标记，避免重复加入同一格。
                grid[r][c] = '0'
                stack = [(r, c)]
                while stack:
                    x, y = stack.pop()
                    # 仅检查四个正交方向。
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < rows and 0 <= ny < cols and grid[nx][ny] == '1':
                            grid[nx][ny] = '0'
                            stack.append((nx, ny))
                # 这次搜索结束，当前整座岛均已标记。
        return islands''',
    '''class Solution {
public:
    int numIslands(vector<vector<char>>& grid) {
        int rows = grid.size(), cols = grid[0].size(), islands = 0;
        int dr[4] = {1, -1, 0, 0}, dc[4] = {0, 0, 1, -1};
        for (int r = 0; r < rows; ++r) for (int c = 0; c < cols; ++c) {
            if (grid[r][c] != '1') continue;
            ++islands;
            // 加入栈的同时标记已访问。
            vector<pair<int, int>> st{{r, c}};
            grid[r][c] = '0';
            while (!st.empty()) {
                auto [x, y] = st.back(); st.pop_back();
                // 岛屿只通过四邻域连接。
                for (int d = 0; d < 4; ++d) {
                    int nx = x + dr[d], ny = y + dc[d];
                    if (nx >= 0 && nx < rows && ny >= 0 && ny < cols && grid[nx][ny] == '1') {
                        grid[nx][ny] = '0'; st.push_back({nx, ny});
                    }
                }
            }
            // 本轮已完整消去一座岛。
        }
        return islands;
    }
};''',
    '每遇到一块未访问陆地，就计一座岛并用深度优先搜索标记整个连通块。',
    ['逐格扫描。', '遇到陆地时计数，并把相连陆地全部标记为水。', '扫描结束返回搜索启动次数。'],
    '每次搜索恰好覆盖起点所在的连通块。标记保证同一连通块不会再启动搜索，不同连通块又不会被同一次搜索访问，故计数恰等于岛屿数。',
    'O(mn)', 'O(mn)，显式搜索栈', ['1 ≤ 行数、列数 ≤ 300', '网格元素仅为字符 "0" 或 "1"'],
    ['输入是字符，不能与整数 1 比较。', '对角接触不算连通。']),

problem(994, '腐烂的橘子', 'rotting-oranges', '中等', '图论',
    '网格中 0 为空，1 为新鲜橘子，2 为腐烂橘子。每分钟所有腐烂橘子同时让上下左右相邻的新鲜橘子腐烂。返回全部橘子腐烂所需最少分钟；无法全部腐烂返回 -1；初始没有新鲜橘子返回 0。',
    [('grid', 'int[][]')], 'int',
    [([[[2, 1, 1], [1, 1, 0], [0, 1, 1]]], 4, '腐烂从起点逐层扩散，最后一格在第 4 分钟腐烂。'), ([[[2, 0, 1]]], -1, '右侧橘子被空格隔开。'), ([[[0, 2]]], 0, '开始时已无新鲜橘子。')],
    'orangesRotting',
    '''from collections import deque

class Solution:
    def orangesRotting(self, grid):
        rows, cols = len(grid), len(grid[0])
        queue, fresh = deque(), 0
        for r in range(rows):
            for c in range(cols):
                if grid[r][c] == 2:
                    queue.append((r, c))
                elif grid[r][c] == 1:
                    fresh += 1
        minutes = 0
        # 所有初始腐烂点同时作为第零层。
        while queue and fresh:
            for _ in range(len(queue)):
                r, c = queue.popleft()
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == 1:
                        # 入队时变色，避免多个来源重复计数。
                        grid[nr][nc] = 2
                        fresh -= 1
                        queue.append((nr, nc))
            minutes += 1
        # 剩余新鲜橘子表示它们不与任何腐烂源连通。
        return minutes if fresh == 0 else -1''',
    '''class Solution {
public:
    int orangesRotting(vector<vector<int>>& grid) {
        int rows = grid.size(), cols = grid[0].size(), fresh = 0, minutes = 0;
        queue<pair<int, int>> q;
        for (int r = 0; r < rows; ++r) for (int c = 0; c < cols; ++c) {
            if (grid[r][c] == 2) q.push({r, c});
            else if (grid[r][c] == 1) ++fresh;
        }
        int dr[4] = {1, -1, 0, 0}, dc[4] = {0, 0, 1, -1};
        // 同一轮队列中的橘子同时向外扩散。
        while (!q.empty() && fresh > 0) {
            int size = q.size();
            while (size--) {
                auto [r, c] = q.front(); q.pop();
                for (int d = 0; d < 4; ++d) {
                    int nr = r + dr[d], nc = c + dc[d];
                    if (nr >= 0 && nr < rows && nc >= 0 && nc < cols && grid[nr][nc] == 1) {
                        // 首次发现即标记，保证只入队一次。
                        grid[nr][nc] = 2; --fresh; q.push({nr, nc});
                    }
                }
            }
            ++minutes;
        }
        // 无法到达的新鲜橘子使任务失败。
        return fresh == 0 ? minutes : -1;
    }
};''',
    '多源广度优先搜索，一层对应一分钟，从所有初始腐烂橘子同时出发。',
    ['把全部腐烂橘子入队并统计新鲜数量。', '逐层扩散并减少新鲜数量。', '新鲜归零返回层数；队列耗尽仍有新鲜则返回 -1。'],
    '广度优先搜索首次到达一格时的层数，是它到任意腐烂源的最短距离，也就是最早腐烂时间。最后被感染的新鲜橘子的层数即全局所需时间。',
    'O(mn)', 'O(mn)', ['1 ≤ 行数、列数 ≤ 10', '元素只能为 0、1、2'],
    ['多个腐烂起点必须同时入队。', '没有新鲜橘子时不要额外增加一分钟。']),

problem(207, '课程表', 'course-schedule', '中等', '图论',
    '共有编号 0 到 numCourses-1 的课程。prerequisites 中 [a,b] 表示选 a 前必须完成 b。判断能否完成所有课程。',
    [('numCourses', 'int'), ('prerequisites', 'int[][]')], 'bool',
    [([2, [[1, 0]]], True, '先修 0 再修 1 即可。'), ([2, [[1, 0], [0, 1]]], False, '两门课互相等待，形成环。'), ([1, []], True, '没有先修限制。')],
    'canFinish',
    '''from collections import deque

class Solution:
    def canFinish(self, numCourses, prerequisites):
        graph = [[] for _ in range(numCourses)]
        indegree = [0] * numCourses
        # 从先修课指向后续课，入度表示剩余先修数量。
        for course, before in prerequisites:
            graph[before].append(course)
            indegree[course] += 1
        queue = deque(i for i in range(numCourses) if indegree[i] == 0)
        finished = 0
        while queue:
            course = queue.popleft()
            finished += 1
            for after in graph[course]:
                # 完成课程会解除后续课程的一项限制。
                indegree[after] -= 1
                if indegree[after] == 0:
                    queue.append(after)
        # 环上的节点永远无法降到零入度。
        return finished == numCourses''',
    '''class Solution {
public:
    bool canFinish(int numCourses, vector<vector<int>>& prerequisites) {
        vector<vector<int>> graph(numCourses);
        vector<int> indegree(numCourses, 0);
        // 边的方向为先修课到后续课。
        for (const auto& edge : prerequisites) {
            graph[edge[1]].push_back(edge[0]); ++indegree[edge[0]];
        }
        queue<int> q;
        for (int i = 0; i < numCourses; ++i) if (indegree[i] == 0) q.push(i);
        int finished = 0;
        while (!q.empty()) {
            int course = q.front(); q.pop(); ++finished;
            // 完成当前课，删除所有从它出发的限制。
            for (int after : graph[course]) if (--indegree[after] == 0) q.push(after);
        }
        // 只有全部节点被取出，才存在完整修课顺序。
        return finished == numCourses;
    }
};''',
    '对先修依赖图做拓扑排序，不断选取当前没有未完成先修课的课程。',
    ['构建邻接表和入度。', '零入度课程入队，完成后减少后继入度。', '检查完成数量是否等于课程总数。'],
    '零入度节点可以安全先完成；删除它不会改变其他课程之间的依赖。若剩余图非空却无零入度节点，则必有有向环；环使修课顺序不可能成立。',
    'O(V + E)', 'O(V + E)', ['1 ≤ numCourses ≤ 2000', '0 ≤ prerequisites.length ≤ 5000', '课程编号有效且先修关系不重复'],
    ['[a,b] 对应 b→a。', '没有依赖的孤立课程也必须计入完成数量。']),

problem(208, '实现 Trie（前缀树）', 'implement-trie-prefix-tree', '中等', '图论',
    '实现 Trie 类：insert(word) 插入单词，search(word) 判断完整单词是否存在，startsWith(prefix) 判断是否存在以该前缀开头的单词。输入为操作名称数组和对应参数数组，构造与插入的输出为 null。',
    [('operations', 'string[]'), ('arguments', 'int[][]')], 'design',
    [([['Trie', 'insert', 'search', 'search', 'startsWith', 'insert', 'search'], [[], ['apple'], ['apple'], ['app'], ['app'], ['app'], ['app']]], [None, None, True, False, True, None, True], '前缀存在并不代表它已作为完整单词插入。'),
     ([['Trie', 'search', 'startsWith', 'insert', 'search'], [[], ['a'], ['a'], ['a'], ['a']]], [None, False, False, None, True], '插入前不存在，插入后可查到。')],
    '',
    '''class Trie:
    def __init__(self):
        self.children = {}
        self.is_word = False

    def insert(self, word):
        node = self
        for char in word:
            # 每条边对应一个字符，公共前缀共享节点。
            if char not in node.children:
                node.children[char] = Trie()
            node = node.children[char]
        node.is_word = True

    def _find(self, text):
        node = self
        for char in text:
            if char not in node.children:
                return None
            node = node.children[char]
        return node

    def search(self, word):
        node = self._find(word)
        # 完整单词需要终止标记。
        return node is not None and node.is_word

    def startsWith(self, prefix):
        # 前缀只要求路径存在。
        return self._find(prefix) is not None''',
    '''class Trie {
    struct Node {
        int child[26];
        bool isWord;
        Node() : isWord(false) { fill(child, child + 26, -1); }
    };
    vector<Node> nodes;
    int findNode(const string& text) {
        int current = 0;
        for (char c : text) {
            current = nodes[current].child[c - 'a'];
            if (current == -1) return -1;
        }
        return current;
    }
public:
    Trie() { nodes.emplace_back(); }
    void insert(string word) {
        int current = 0;
        for (char c : word) {
            int index = c - 'a';
            // 用整数下标保存孩子，容器扩容不会使下标失效。
            if (nodes[current].child[index] == -1) {
                int next = nodes.size();
                nodes.emplace_back();
                nodes[current].child[index] = next;
            }
            current = nodes[current].child[index];
        }
        nodes[current].isWord = true;
    }
    bool search(string word) {
        int index = findNode(word);
        // 完整单词必须有结束标记。
        return index != -1 && nodes[index].isWord;
    }
    bool startsWith(string prefix) {
        // 前缀不要求位于单词结尾。
        return findNode(prefix) != -1;
    }
};''',
    '以字符为边建立前缀树，共享重复前缀，额外记录某节点是否是单词终点。',
    ['插入时沿字符路径前进，按需创建节点。', '查单词时先找到完整路径，再检查终点标记。', '查前缀只检查路径是否存在。'],
    '每个节点对应根到它的唯一字符串。插入恰好构造该字符串路径并标记终点；因此路径存在等价于前缀存在，路径终点被标记等价于该单词已插入。',
    '每次操作 O(L)，L 为传入字符串长度', 'O(S)，S 为插入单词总字符数', ['字符均为小写英文字母', '1 ≤ 单词或前缀长度 ≤ 2000', '操作总次数 ≤ 30000'],
    ['search 必须检查结束标记。', 'C++ vector 扩容后不能继续使用之前的节点引用。'], special='design', className='Trie'),

problem(46, '全排列', 'permutations', '中等', '回溯算法',
    '给定没有重复元素的整数数组 nums，返回使用每个元素恰好一次构成的所有排列。答案排列之间的顺序不限。',
    [('nums', 'int[]')], 'int[][]',
    [([[1, 2, 3]], [[1, 2, 3], [1, 3, 2], [2, 1, 3], [2, 3, 1], [3, 1, 2], [3, 2, 1]], '三个不同元素有 6 种排列。'), ([[0]], [[0]], '单元素只有一种排列。')],
    'permute',
    '''class Solution:
    def permute(self, nums):
        result, path = [], []
        used = [False] * len(nums)
        def backtrack():
            if len(path) == len(nums):
                # 保存副本，防止之后撤销影响答案。
                result.append(path.copy())
                return
            for i, value in enumerate(nums):
                if used[i]:
                    continue
                # 选择当前尚未使用的元素。
                used[i] = True
                path.append(value)
                backtrack()
                # 撤销选择，让其他分支可以使用它。
                path.pop()
                used[i] = False
        backtrack()
        return result''',
    '''class Solution {
public:
    vector<vector<int>> permute(vector<int>& nums) {
        vector<vector<int>> result;
        vector<int> path;
        vector<bool> used(nums.size(), false);
        function<void()> backtrack = [&]() {
            // 复制完整排列作为独立答案。
            if (path.size() == nums.size()) { result.push_back(path); return; }
            for (int i = 0; i < static_cast<int>(nums.size()); ++i) {
                if (used[i]) continue;
                // 选择一个未使用的元素。
                used[i] = true; path.push_back(nums[i]);
                backtrack();
                // 恢复进入该分支之前的状态。
                path.pop_back(); used[i] = false;
            }
        };
        backtrack();
        return result;
    }
};''',
    '按位置依次选择尚未使用的元素，使用标记数组避免重复选取。',
    ['维护当前排列与 used 数组。', '枚举未使用元素加入路径。', '长度达到 n 后保存；递归返回时撤销。'],
    '每层填一个位置，每个位置遍历所有可用元素。因此每个合法排列对应唯一的一条选择路径，全部被生成且不会重复。',
    'O(n·n!)', 'O(n)，不计答案', ['1 ≤ nums.length ≤ 6', '元素互不重复'],
    ['排列中的顺序有意义，不能使用只向右递增的起点限制。', '保存路径时必须复制。'], compare='unordered'),

problem(78, '子集', 'subsets', '中等', '回溯算法',
    '给定元素互不相同的整数数组，返回全部子集，包括空集和全集。子集内及子集之间的顺序不限，不得重复。',
    [('nums', 'int[]')], 'int[][]',
    [([[1, 2, 3]], [[], [1], [2], [3], [1, 2], [1, 3], [2, 3], [1, 2, 3]], '每个元素有选和不选两种状态，共 8 个子集。'), ([[0]], [[], [0]], '包含空集和单元素集合。')],
    'subsets',
    '''class Solution:
    def subsets(self, nums):
        result, path = [], []
        def backtrack(start):
            # 任意长度的当前路径都是一个合法子集。
            result.append(path.copy())
            for i in range(start, len(nums)):
                path.append(nums[i])
                # 下标严格递增，避免同一组合的不同排列。
                backtrack(i + 1)
                # 回到当前层继续枚举下一个选择。
                path.pop()
        backtrack(0)
        return result''',
    '''class Solution {
public:
    vector<vector<int>> subsets(vector<int>& nums) {
        vector<vector<int>> result;
        vector<int> path;
        function<void(int)> backtrack = [&](int start) {
            // 每个递归节点都代表一个不同子集。
            result.push_back(path);
            for (int i = start; i < static_cast<int>(nums.size()); ++i) {
                path.push_back(nums[i]);
                // 之后只选择更大下标，避免重复。
                backtrack(i + 1);
                // 撤销本层选择。
                path.pop_back();
            }
        };
        backtrack(0);
        return result;
    }
};''',
    '按递增下标选择元素，每个递归节点都保存一个子集。',
    ['先保存当前路径，包括初始空集。', '枚举从 start 开始的元素。', '递归只考虑其后的元素，返回后撤销。'],
    '任何子集都能唯一表示为递增下标序列。回溯枚举所有这种序列，因此结果完整且没有重复。',
    'O(n·2^n)', 'O(n)，不计答案', ['1 ≤ nums.length ≤ 10', '元素互不重复'],
    ['不应只在叶节点保存答案。', '递归下一起点是 i+1。'], compare='groups'),

problem(17, '电话号码的字母组合', 'letter-combinations-of-a-phone-number', '中等', '回溯算法',
    '数字 2 到 9 对应电话键盘字母：2→abc、3→def、4→ghi、5→jkl、6→mno、7→pqrs、8→tuv、9→wxyz。给定数字字符串，返回依次从每位对应字母中各选一个得到的全部字符串；空输入返回空数组。',
    [('digits', 'string')], 'string[]',
    [(['23'], ['ad', 'ae', 'af', 'bd', 'be', 'bf', 'cd', 'ce', 'cf'], '每个结果依次取一个 2 对应字母和一个 3 对应字母。'), ([''], [], '没有数字时无组合。')],
    'letterCombinations',
    '''class Solution:
    def letterCombinations(self, digits):
        if not digits:
            return []
        letters = ['', '', 'abc', 'def', 'ghi', 'jkl', 'mno', 'pqrs', 'tuv', 'wxyz']
        result, path = [], []
        def backtrack(index):
            if index == len(digits):
                # 每一位数字都已匹配一个字母。
                result.append(''.join(path))
                return
            # 这一层只选择当前数字对应的字母。
            for char in letters[int(digits[index])]:
                path.append(char)
                backtrack(index + 1)
                # 撤销以尝试同一数字的其他字母。
                path.pop()
        backtrack(0)
        return result''',
    '''class Solution {
public:
    vector<string> letterCombinations(string digits) {
        if (digits.empty()) return {};
        vector<string> letters{"", "", "abc", "def", "ghi", "jkl", "mno", "pqrs", "tuv", "wxyz"};
        vector<string> result;
        string path;
        function<void(int)> backtrack = [&](int index) {
            // 长度达到数字个数时保存字符串。
            if (index == static_cast<int>(digits.size())) { result.push_back(path); return; }
            // 只枚举当前按键上的字母。
            for (char c : letters[digits[index] - '0']) {
                path.push_back(c);
                backtrack(index + 1);
                // 为同层的下一个字母恢复路径。
                path.pop_back();
            }
        };
        backtrack(0);
        return result;
    }
};''',
    '按数字位置回溯，逐位从该按键对应的字母表中选择。',
    ['空输入直接返回空数组。', '递归处理当前数字并枚举字母。', '所有位置处理后合并并保存字符串。'],
    '每个合法字符串在第 i 位恰好选择 digits[i] 的一个字母。回溯对这些独立选择做笛卡尔积，因每条路径选择序列不同，所有组合恰好出现一次。',
    'O(n·4^n)，最坏情况', 'O(n)，不计答案', ['0 ≤ digits.length ≤ 4', 'digits 仅包含 2 到 9'],
    ['7 和 9 对应四个字母。', '空字符串的结果应为 []，不是 [""]。'], compare='unordered'),

problem(39, '组合总和', 'combination-sum', '中等', '回溯算法',
    '给定互不相同的正整数 candidates 和目标 target，返回元素之和为 target 的全部组合。每个数可重复使用任意次；组合中元素顺序不重要，同一组合不能重复。',
    [('candidates', 'int[]'), ('target', 'int')], 'int[][]',
    [([[2, 3, 6, 7], 7], [[2, 2, 3], [7]], '2 可以重复使用。'), ([[2], 1], [], '最小候选数也超过目标，无法组成。')],
    'combinationSum',
    '''class Solution:
    def combinationSum(self, candidates, target):
        # 排序使超过剩余目标时可以直接终止枚举。
        candidates = sorted(candidates)
        result, path = [], []
        def backtrack(start, remaining):
            if remaining == 0:
                result.append(path.copy())
                return
            for i in range(start, len(candidates)):
                value = candidates[i]
                if value > remaining:
                    break
                path.append(value)
                # 仍从 i 开始，允许再次选当前数字。
                backtrack(i, remaining - value)
                # 撤销后才能尝试其他候选数。
                path.pop()
        backtrack(0, target)
        return result''',
    '''class Solution {
public:
    vector<vector<int>> combinationSum(vector<int>& candidates, int target) {
        // 排序便于剪掉后续必定过大的候选数。
        sort(candidates.begin(), candidates.end());
        vector<vector<int>> result;
        vector<int> path;
        function<void(int, int)> backtrack = [&](int start, int remaining) {
            if (remaining == 0) { result.push_back(path); return; }
            for (int i = start; i < static_cast<int>(candidates.size()); ++i) {
                int value = candidates[i];
                if (value > remaining) break;
                path.push_back(value);
                // 下一层仍能使用下标 i。
                backtrack(i, remaining - value);
                // 恢复路径以遍历其他组合。
                path.pop_back();
            }
        };
        backtrack(0, target);
        return result;
    }
};''',
    '排序后按照非递减下标回溯，允许重复选取同一下标，并根据剩余和剪枝。',
    ['排序候选数。', '枚举从 start 开始且不超过剩余和的数字。', '递归保持当前下标；剩余和为零时保存组合。'],
    '每个组合都有唯一的非递减序列表示。回溯枚举所有这样的序列；正数保证剩余和持续下降，超过剩余和的候选不可能参与答案，因此剪枝安全。',
    'O(N log N + N^D·D) 的宽松上界，D=⌊target/min(candidates)⌋；实际取决于搜索和输出',
    'O(N + D)，不计答案', ['1 ≤ candidates.length ≤ 30', '2 ≤ candidates[i] ≤ 40，且互不相同', '1 ≤ target ≤ 40'],
    ['下一层起点为 i，写成 i+1 会禁止重复使用。', '只在 remaining 为 0 时保存答案。'], compare='groups'),

problem(22, '括号生成', 'generate-parentheses', '中等', '回溯算法',
    '给定正整数 n，生成恰好包含 n 对圆括号的所有合法括号字符串。合法意味着任意前缀中右括号数量不超过左括号数量，且最终两者相等。',
    [('n', 'int')], 'string[]',
    [([3], ['((()))', '(()())', '(())()', '()(())', '()()()'], '3 对括号共有 5 种合法排列。'), ([1], ['()'], '一对括号仅有一种合法写法。')],
    'generateParenthesis',
    '''class Solution:
    def generateParenthesis(self, n):
        result, path = [], []
        def backtrack(left, right):
            if right == n:
                # 两种括号都已经放满。
                result.append(''.join(path))
                return
            if left < n:
                # 左括号只受总数量限制。
                path.append('(')
                backtrack(left + 1, right)
                path.pop()
            if right < left:
                # 右括号必须有未匹配的左括号可配对。
                path.append(')')
                backtrack(left, right + 1)
                path.pop()
        backtrack(0, 0)
        return result''',
    '''class Solution {
public:
    vector<string> generateParenthesis(int n) {
        vector<string> result;
        string path;
        function<void(int, int)> backtrack = [&](int left, int right) {
            // 右括号达到 n 时，整个串已经完成。
            if (right == n) { result.push_back(path); return; }
            // 左括号数量不能超过 n。
            if (left < n) {
                path.push_back('('); backtrack(left + 1, right); path.pop_back();
            }
            // 任何前缀都不能出现过量的右括号。
            if (right < left) {
                path.push_back(')'); backtrack(left, right + 1); path.pop_back();
            }
        };
        backtrack(0, 0);
        return result;
    }
};''',
    '回溯时直接维护合法前缀，只在仍有配额时加左括号、存在未匹配左括号时加右括号。',
    ['记录已放左、右括号数量。', '满足 left<n 时尝试左括号，right<left 时尝试右括号。', '放满 n 个右括号时保存。'],
    '两个限制保证每个生成前缀合法，结束时恰有 n 对。任何合法字符串的每一步都满足这两个限制，因此它对应的一条回溯路径不会被剪去。',
    'O(n·Cₙ)，Cₙ 为第 n 个卡特兰数', 'O(n)，不计答案', ['1 ≤ n ≤ 8'],
    ['允许右括号的条件是 right<left，而不是 right<n。', '不必先生成所有字符串再验证。'], compare='unordered'),

problem(79, '单词搜索', 'word-search', '中等', '回溯算法',
    '给定字符网格 board 和单词 word，判断能否从任意格出发，沿上下左右相邻格依次拼出单词。同一次路径中每格最多使用一次。',
    [('board', 'char[][]'), ('word', 'string')], 'bool',
    [([[['A', 'B', 'C', 'E'], ['S', 'F', 'C', 'S'], ['A', 'D', 'E', 'E']], 'ABCCED'], True, '可以沿不重复的相邻格拼出目标。'), ([[['A', 'A']], 'AAA'], False, '只有两个格，不能重复使用同一格。')],
    'exist',
    '''from collections import Counter

class Solution:
    def exist(self, board, word):
        rows, cols = len(board), len(board[0])
        available = Counter(char for row in board for char in row)
        needed = Counter(word)
        # 字符总量不足时，无需进入指数搜索。
        if any(needed[c] > available[c] for c in needed):
            return False
        if available[word[0]] > available[word[-1]]:
            word = word[::-1]
        def search(r, c, index):
            if not (0 <= r < rows and 0 <= c < cols) or board[r][c] != word[index]:
                return False
            if index == len(word) - 1:
                return True
            char = board[r][c]
            # 临时标记本路径已使用的格子。
            board[r][c] = '#'
            found = any(search(r + dr, c + dc, index + 1)
                        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            # 成功或失败都恢复，确保输入不会残留标记。
            board[r][c] = char
            return found
        return any(search(r, c, 0) for r in range(rows) for c in range(cols))''',
    '''class Solution {
public:
    bool exist(vector<vector<char>>& board, string word) {
        int rows = board.size(), cols = board[0].size();
        int available[128] = {}, needed[128] = {};
        for (const auto& row : board) for (char c : row) ++available[static_cast<unsigned char>(c)];
        for (char c : word) ++needed[static_cast<unsigned char>(c)];
        // 字符数量不足时直接剪枝。
        for (int i = 0; i < 128; ++i) if (needed[i] > available[i]) return false;
        if (available[static_cast<unsigned char>(word.front())] > available[static_cast<unsigned char>(word.back())]) reverse(word.begin(), word.end());
        int dr[4] = {1, -1, 0, 0}, dc[4] = {0, 0, 1, -1};
        function<bool(int, int, int)> search = [&](int r, int c, int index) {
            if (r < 0 || r >= rows || c < 0 || c >= cols || board[r][c] != word[index]) return false;
            if (index + 1 == static_cast<int>(word.size())) return true;
            // 标记本路径已经使用的格子。
            char saved = board[r][c]; board[r][c] = '#';
            bool found = false;
            for (int d = 0; d < 4 && !found; ++d) found = search(r + dr[d], c + dc[d], index + 1);
            // 不论结果如何都恢复棋盘。
            board[r][c] = saved;
            return found;
        };
        for (int r = 0; r < rows; ++r) for (int c = 0; c < cols; ++c) if (search(r, c, 0)) return true;
        return false;
    }
};''',
    '先用字符数量做必要条件剪枝，再从起点进行不重复使用格子的深度优先回溯。从较稀有的一端搜索可减少起点。',
    ['检查每种字符是否充足，必要时反转单词以减少起点。', '当前字符匹配后暂时标记格子，再尝试四邻格。', '退出分支前恢复原字符；任一路径匹配全部字符即成功。'],
    '搜索枚举所有以合法相邻格扩展且不重复使用格子的路径，字符检查只保留正确前缀。任意目标路径及其逆序都保持邻接，因此反转单词不改变是否存在的结论。',
    'O(mn·3^L)，L 为单词长度，常数包含起点四个方向', 'O(L)，递归栈；字符表大小固定', ['1 ≤ 行数、列数 ≤ 6', '1 ≤ word.length ≤ 15', '字符均为大小写英文字母'],
    ['visited 只针对当前路径，回溯必须撤销。', '格子只能上下左右相邻，不能走对角。']),

problem(131, '分割回文串', 'palindrome-partitioning', '中等', '回溯算法',
    '将字符串 s 切分为一个或多个连续的非空子串，要求每段都是回文。返回所有满足条件的切分方式；每种方式必须按原字符串顺序列出各段。',
    [('s', 'string')], 'string[][]',
    [(['aab'], [['a', 'a', 'b'], ['aa', 'b']], 'aa 为回文，aab 不是回文。'), (['a'], [['a']], '单字符本身是回文。')],
    'partition',
    '''class Solution:
    def partition(self, s):
        n = len(s)
        palindrome = [[False] * n for _ in range(n)]
        # 按左端点递减计算，保证内部短区间已经就绪。
        for left in range(n - 1, -1, -1):
            for right in range(left, n):
                palindrome[left][right] = (s[left] == s[right] and
                    (right - left < 2 or palindrome[left + 1][right - 1]))
        result, path = [], []
        def backtrack(start):
            if start == n:
                result.append(path.copy())
                return
            for end in range(start, n):
                # 仅当当前片段是回文时才继续切后半段。
                if palindrome[start][end]:
                    path.append(s[start:end + 1])
                    backtrack(end + 1)
                    # 撤销最后一段，尝试更长片段。
                    path.pop()
        backtrack(0)
        return result''',
    '''class Solution {
public:
    vector<vector<string>> partition(string s) {
        int n = s.size();
        vector<vector<bool>> palindrome(n, vector<bool>(n, false));
        // 子区间先就绪，再判断外侧两个字符。
        for (int left = n - 1; left >= 0; --left) for (int right = left; right < n; ++right)
            palindrome[left][right] = s[left] == s[right] && (right - left < 2 || palindrome[left + 1][right - 1]);
        vector<vector<string>> result;
        vector<string> path;
        function<void(int)> backtrack = [&](int start) {
            if (start == n) { result.push_back(path); return; }
            for (int end = start; end < n; ++end) {
                // 查询预处理表，常数时间确认回文。
                if (!palindrome[start][end]) continue;
                path.push_back(s.substr(start, end - start + 1));
                backtrack(end + 1);
                // 撤销当前分段，继续枚举切点。
                path.pop_back();
            }
        };
        backtrack(0);
        return result;
    }
};''',
    '动态规划预先判断所有区间是否回文，再回溯枚举每段终点。',
    ['用两端字符相等且内部回文计算区间表。', '从当前位置枚举回文片段。', '递归分割剩余后缀，耗尽字符串时保存方案。'],
    '预处理递推正好对应回文定义。任意合法切分有唯一的切点序列，回溯会逐一选择这些切点；非回文段被排除，因此结果完整且全部合法。',
    'O(n² + n·2^n)', 'O(n²)，不计答案', ['1 ≤ s.length ≤ 16', 's 仅包含小写英文字母'],
    ['分段顺序必须保留，不能在答案内部排序。', '长度 1 和 2 的回文边界需要单独覆盖。'], compare='unordered'),

problem(51, 'N 皇后', 'n-queens', '困难', '回溯算法',
    '在 n×n 棋盘上放置 n 个皇后，使任意两个皇后都不在同一行、同一列或同一条斜线上。返回全部棋盘方案，用 Q 表示皇后、. 表示空格，每个方案按行存储。',
    [('n', 'int')], 'string[][]',
    [([4], [['.Q..', '...Q', 'Q...', '..Q.'], ['..Q.', 'Q...', '...Q', '.Q..']], '4 皇后共有两种方案。'), ([1], [['Q']], '唯一格子放置一个皇后。'), ([2], [], '2×2 棋盘无合法方案。')],
    'solveNQueens',
    '''class Solution:
    def solveNQueens(self, n):
        result, placement = [], []
        columns, diagonals_down, diagonals_up = set(), set(), set()
        def backtrack(row):
            if row == n:
                # 只在答案完成时生成字符串棋盘。
                result.append(['.' * col + 'Q' + '.' * (n - col - 1) for col in placement])
                return
            for col in range(n):
                # 同一斜线分别由行列差、行列和标识。
                if col in columns or row - col in diagonals_down or row + col in diagonals_up:
                    continue
                placement.append(col)
                columns.add(col)
                diagonals_down.add(row - col)
                diagonals_up.add(row + col)
                backtrack(row + 1)
                # 恢复占用信息供同层后续选择使用。
                placement.pop()
                columns.remove(col)
                diagonals_down.remove(row - col)
                diagonals_up.remove(row + col)
        backtrack(0)
        return result''',
    '''class Solution {
public:
    vector<vector<string>> solveNQueens(int n) {
        vector<vector<string>> result;
        vector<int> placement;
        vector<bool> columns(n, false), down(2 * n - 1, false), up(2 * n - 1, false);
        function<void(int)> backtrack = [&](int row) {
            if (row == n) {
                // 搜索期间只保存列位置，完成时生成棋盘。
                vector<string> board(n, string(n, '.'));
                for (int r = 0; r < n; ++r) board[r][placement[r]] = 'Q';
                result.push_back(board); return;
            }
            for (int col = 0; col < n; ++col) {
                // 行列差加偏移后可直接作为数组下标。
                int d = row - col + n - 1, u = row + col;
                if (columns[col] || down[d] || up[u]) continue;
                placement.push_back(col); columns[col] = down[d] = up[u] = true;
                backtrack(row + 1);
                // 撤销本行占用的列和两条斜线。
                placement.pop_back(); columns[col] = down[d] = up[u] = false;
            }
        };
        backtrack(0);
        return result;
    }
};''',
    '逐行放皇后，用列、行列差和行列和三组占用记录，在常数时间判断冲突。',
    ['每层处理一行，枚举可用列。', '检查该列与两条斜线是否占用。', '放置后递归下一行，再撤销；全部行完成时生成棋盘。'],
    '一行只放一个皇后，三组标记排除了列和斜线冲突。任意合法棋盘都有唯一的逐行列选择序列，搜索会枚举该序列且不会错误剪枝。',
    'O(n·n! + K·n²)，K 为方案数；前项为搜索的保守上界', 'O(n)，不计棋盘输出', ['1 ≤ n ≤ 9'],
    ['两类斜线分别使用 row-col 和 row+col。', '退出分支必须同时撤销三种占用信息。'], compare='unordered'),

problem(35, '搜索插入位置', 'search-insert-position', '简单', '二分查找',
    '给定严格递增数组 nums 和 target。若目标存在，返回它的下标；否则返回保持递增顺序时应插入的位置。要求对数时间。',
    [('nums', 'int[]'), ('target', 'int')], 'int',
    [([[1, 3, 5, 6], 5], 2, '目标已存在于下标 2。'), ([[1, 3, 5, 6], 7], 4, '目标应插到数组末尾。')],
    'searchInsert',
    '''class Solution:
    def searchInsert(self, nums, target):
        # 在左闭右开区间寻找第一个不小于 target 的位置。
        left, right = 0, len(nums)
        while left < right:
            mid = (left + right) // 2
            if nums[mid] < target:
                # mid 及左侧都太小。
                left = mid + 1
            else:
                # mid 可能正是答案，需要保留。
                right = mid
        return left''',
    '''class Solution {
public:
    int searchInsert(vector<int>& nums, int target) {
        // 右端点可取 size，表示插入到末尾。
        int left = 0, right = nums.size();
        while (left < right) {
            int mid = left + (right - left) / 2;
            // 所有小于 target 的元素都应位于答案之前。
            if (nums[mid] < target) left = mid + 1;
            // 保留可能是答案的 mid。
            else right = mid;
        }
        return left;
    }
};''',
    '用下界二分寻找首个大于等于 target 的位置。',
    ['搜索区间初始化为 [0,n)。', '中点值太小则舍弃中点及左半段，否则保留中点并缩右界。', '两界相遇即返回。'],
    '整个过程中 left 之前都小于 target，right 及之后都不小于 target。两界相遇时唯一分界点既是已存在目标的位置，也是正确插入位置。',
    'O(log n)', 'O(1)', ['1 ≤ nums.length ≤ 10000', 'nums 严格递增', '数值在 32 位有符号整数范围内'],
    ['未找到时也返回分界点，无需另分支。', '右边界初始化为 n 而非 n-1。']),

problem(74, '搜索二维矩阵', 'search-a-2d-matrix', '中等', '二分查找',
    '矩阵每行递增，且每行首元素严格大于前一行末元素。判断 target 是否在矩阵中，要求 O(log(mn)) 时间。',
    [('matrix', 'int[][]'), ('target', 'int')], 'bool',
    [([[[1, 3, 5, 7], [10, 11, 16, 20], [23, 30, 34, 60]], 3], True, '第一行包含 3。'), ([[[1]], 2], False, '唯一元素不等于目标。')],
    'searchMatrix',
    '''class Solution:
    def searchMatrix(self, matrix, target):
        rows, cols = len(matrix), len(matrix[0])
        # 按行展开后的虚拟数组是整体有序的。
        left, right = 0, rows * cols - 1
        while left <= right:
            mid = (left + right) // 2
            # 除法映射行号，取余映射列号，无需实际展开。
            value = matrix[mid // cols][mid % cols]
            if value == target:
                return True
            # 按大小关系舍弃不可能存在目标的一半。
            if value < target:
                left = mid + 1
            else:
                right = mid - 1
        return False''',
    '''class Solution {
public:
    bool searchMatrix(vector<vector<int>>& matrix, int target) {
        int rows = matrix.size(), cols = matrix[0].size();
        // 把二维矩阵视为按行排列的一维有序序列。
        int left = 0, right = rows * cols - 1;
        while (left <= right) {
            int mid = left + (right - left) / 2;
            // 通过整除与取余还原真实坐标。
            int value = matrix[mid / cols][mid % cols];
            if (value == target) return true;
            // 标准闭区间二分。
            if (value < target) left = mid + 1;
            else right = mid - 1;
        }
        return false;
    }
};''',
    '将矩阵视为虚拟的一维有序数组，通过下标换算进行二分。',
    ['在 0 到 mn-1 的下标区间二分。', '中点映射为行 mid/cols、列 mid%cols。', '按大小缩小区间或找到即返回。'],
    '行内有序且行间严格分隔，保证按行展开整体有序。因此标准二分的舍弃规则成立，坐标映射又与展开序列一一对应，判断结果正确。',
    'O(log(mn))', 'O(1)', ['1 ≤ 行数、列数 ≤ 100', '矩阵满足题目给定的整体有序条件'],
    ['除数必须是列数，不是行数。', '仅行列各自有序的另一类矩阵不能直接使用此方法。']),

problem(34, '在排序数组中查找元素的第一个和最后一个位置', 'find-first-and-last-position-of-element-in-sorted-array', '中等', '二分查找',
    '给定非递减整数数组 nums，返回 target 第一次与最后一次出现的下标。没有目标则返回 [-1,-1]，要求 O(log n) 时间。',
    [('nums', 'int[]'), ('target', 'int')], 'int[]',
    [([[5, 7, 7, 8, 8, 10], 8], [3, 4], '目标出现在连续区间 [3,4]。'), ([[], 0], [-1, -1], '空数组不包含目标。')],
    'searchRange',
    '''class Solution:
    def searchRange(self, nums, target):
        def boundary(strict):
            left, right = 0, len(nums)
            while left < right:
                mid = (left + right) // 2
                # strict 为真时越过等于目标的元素，寻找右边界。
                if nums[mid] < target or (strict and nums[mid] == target):
                    left = mid + 1
                else:
                    right = mid
            return left
        first = boundary(False)
        # 左边界可能等于 n，须先检查再访问数组。
        if first == len(nums) or nums[first] != target:
            return [-1, -1]
        # 首个大于目标的位置再减一，就是最后一次出现。
        return [first, boundary(True) - 1]''',
    '''class Solution {
public:
    vector<int> searchRange(vector<int>& nums, int target) {
        auto boundary = [&](bool strict) {
            int left = 0, right = nums.size();
            while (left < right) {
                int mid = left + (right - left) / 2;
                // strict 控制相等值应被舍弃还是保留。
                if (nums[mid] < target || (strict && nums[mid] == target)) left = mid + 1;
                else right = mid;
            }
            return left;
        };
        int first = boundary(false);
        // 先检查越界，再验证目标是否存在。
        if (first == static_cast<int>(nums.size()) || nums[first] != target) return {-1, -1};
        // 开放右边界转成最后一个目标的下标。
        return {first, boundary(true) - 1};
    }
};''',
    '二分查找首个大于等于目标的位置和首个严格大于目标的位置，得到闭区间两端。',
    ['第一次二分求下界。', '若下界越界或值不等于目标，返回不存在。', '第二次二分求上界，再减一作为末位置。'],
    '有序数组中相等元素必连续。下界之前全小于目标，上界及之后全大于目标，因此两界之间恰好是全部目标元素。',
    'O(log n)', 'O(1)', ['0 ≤ nums.length ≤ 100000', 'nums 非递减，允许重复值'],
    ['找到任意目标后线性扩展会退化为 O(n)。', '不用 target+1 求上界，避免整数溢出。']),

problem(33, '搜索旋转排序数组', 'search-in-rotated-sorted-array', '中等', '二分查找',
    '一个严格递增数组在某处旋转后得到 nums，元素仍互不相同。用 O(log n) 时间返回 target 的下标，不存在返回 -1。',
    [('nums', 'int[]'), ('target', 'int')], 'int',
    [([[4, 5, 6, 7, 0, 1, 2], 0], 4, '目标位于旋转后的下标 4。'), ([[1], 0], -1, '单元素数组不含目标。')],
    'search',
    '''class Solution:
    def search(self, nums, target):
        left, right = 0, len(nums) - 1
        while left <= right:
            mid = (left + right) // 2
            if nums[mid] == target:
                return mid
            # 中点两侧至少有一侧是正常递增的。
            if nums[left] <= nums[mid]:
                # 左侧有序：用值域判断目标是否落在其中。
                if nums[left] <= target < nums[mid]:
                    right = mid - 1
                else:
                    left = mid + 1
            else:
                # 右侧有序，同样检查其值域。
                if nums[mid] < target <= nums[right]:
                    left = mid + 1
                else:
                    right = mid - 1
        return -1''',
    '''class Solution {
public:
    int search(vector<int>& nums, int target) {
        int left = 0, right = static_cast<int>(nums.size()) - 1;
        while (left <= right) {
            int mid = left + (right - left) / 2;
            if (nums[mid] == target) return mid;
            // 元素互异保证至少一侧有序且可明确判断。
            if (nums[left] <= nums[mid]) {
                // 目标在左侧的值域中时保留左半段。
                if (nums[left] <= target && target < nums[mid]) right = mid - 1;
                else left = mid + 1;
            } else {
                // 否则右侧有序，用它的值域做判断。
                if (nums[mid] < target && target <= nums[right]) left = mid + 1;
                else right = mid - 1;
            }
        }
        return -1;
    }
};''',
    '每轮先识别有序的一半，再根据目标是否落入该半段的值域决定保留哪侧。',
    ['先比较中点与目标。', '通过左端与中点关系判断左半段是否有序。', '检查有序半段的范围，舍弃另一半或该半段。'],
    '旋转只产生一个断点，因此左右半段至少一段有序。有序段的值域可以准确判断目标归属，每轮舍弃的半段不包含目标，区间不断缩小直到找到或为空。',
    'O(log n)', 'O(1)', ['1 ≤ nums.length ≤ 5000', '元素互不重复，数组由递增数组旋转得到'],
    ['nums[left]<=nums[mid] 中的等号用于单元素半段。', '此方案依赖元素互异。']),

problem(153, '寻找旋转排序数组中的最小值', 'find-minimum-in-rotated-sorted-array', '中等', '二分查找',
    '给定由严格递增数组旋转得到的非空数组 nums，元素互不相同。以 O(log n) 时间返回最小元素。数组也可能保持原顺序。',
    [('nums', 'int[]')], 'int',
    [([[3, 4, 5, 1, 2]], 1, '旋转断点处是最小值。'), ([[1]], 1, '单元素直接就是最小值。'), ([[1, 2, 3]], 1, '没有发生有效旋转时最小值在开头。')],
    'findMin',
    '''class Solution:
    def findMin(self, nums):
        left, right = 0, len(nums) - 1
        while left < right:
            mid = (left + right) // 2
            # 中点大于右端，断点必在中点右边。
            if nums[mid] > nums[right]:
                left = mid + 1
            else:
                # 中点到右端有序，最小值在左侧且可能是中点。
                right = mid
        # 闭区间收缩为唯一候选。
        return nums[left]''',
    '''class Solution {
public:
    int findMin(vector<int>& nums) {
        int left = 0, right = static_cast<int>(nums.size()) - 1;
        while (left < right) {
            int mid = left + (right - left) / 2;
            // 中点位于高值段时，最小值一定在其右侧。
            if (nums[mid] > nums[right]) left = mid + 1;
            // 否则保留中点，避免丢失最小值。
            else right = mid;
        }
        // 最终区间只有一个元素。
        return nums[left];
    }
};''',
    '比较中点与右端点，判断中点位于旋转断点的哪一侧。',
    ['初始化包含最小值的闭区间。', '中点大于右端时向右收缩，否则右界移到中点。', '返回最终唯一候选值。'],
    '若中点大于右端，则中点在较高段，最小值必在右侧；否则中点到右端单调递增，最小值不可能在中点之后。每次保留区间都包含真正最小值。',
    'O(log n)', 'O(1)', ['1 ≤ nums.length ≤ 5000', '元素互不相同，数组由递增数组旋转得到'],
    ['右界更新为 mid，不能是 mid-1。', '比较对象使用当前右端点。']),

problem(4, '寻找两个正序数组的中位数', 'median-of-two-sorted-arrays', '困难', '二分查找',
    '给定两个非递减整数数组 nums1、nums2，至少一个非空。返回把两者合并排序后的中位数：奇数长度取中间值，偶数长度取中间两值的平均数。要求 O(log(m+n)) 时间。',
    [('nums1', 'int[]'), ('nums2', 'int[]')], 'double',
    [([[1, 3], [2]], 2.0, '合并序列为 1、2、3，中间值为 2。'), ([[], [1, 2]], 1.5, '一个数组可为空，中位数是 (1+2)/2。')],
    'findMedianSortedArrays',
    '''class Solution:
    def findMedianSortedArrays(self, nums1, nums2):
        # 只在较短数组二分，确保另一数组的切分位置合法。
        if len(nums1) > len(nums2):
            nums1, nums2 = nums2, nums1
        m, n = len(nums1), len(nums2)
        left, right = 0, m
        half = (m + n + 1) // 2
        while left <= right:
            i = (left + right) // 2
            j = half - i
            # 无元素的一侧使用无穷哨兵统一处理边界。
            a_left = nums1[i - 1] if i else float('-inf')
            a_right = nums1[i] if i < m else float('inf')
            b_left = nums2[j - 1] if j else float('-inf')
            b_right = nums2[j] if j < n else float('inf')
            if a_left > b_right:
                right = i - 1
            elif b_left > a_right:
                left = i + 1
            else:
                # 左区全部不大于右区，切分符合中位数定义。
                if (m + n) % 2:
                    return float(max(a_left, b_left))
                return (max(a_left, b_left) + min(a_right, b_right)) / 2''',
    '''class Solution {
public:
    double findMedianSortedArrays(vector<int>& nums1, vector<int>& nums2) {
        // 在较短数组上二分，不复制数组。
        if (nums1.size() > nums2.size()) return findMedianSortedArrays(nums2, nums1);
        int m = nums1.size(), n = nums2.size();
        int left = 0, right = m, half = (m + n + 1) / 2;
        while (left <= right) {
            int i = left + (right - left) / 2, j = half - i;
            // 哨兵让空边界也能使用统一比较。
            long long aLeft = i ? nums1[i - 1] : LLONG_MIN;
            long long aRight = i < m ? nums1[i] : LLONG_MAX;
            long long bLeft = j ? nums2[j - 1] : LLONG_MIN;
            long long bRight = j < n ? nums2[j] : LLONG_MAX;
            if (aLeft > bRight) right = i - 1;
            else if (bLeft > aRight) left = i + 1;
            else {
                // 合法切分后，中间值就在左右边界。
                if ((m + n) % 2) return static_cast<double>(max(aLeft, bLeft));
                return (static_cast<double>(max(aLeft, bLeft)) + min(aRight, bRight)) / 2.0;
            }
        }
        return 0.0; // 有效有序输入一定存在合法切分。
    }
};''',
    '二分较短数组的切分位置，使合并后的左区数量固定，且左区所有值不大于右区所有值。',
    ['保证第一个数组较短，并令左区元素总数为 (m+n+1)//2。', '由第一个切分位置推出第二个位置，比较四个边界值。', '左侧边界过大就左移，另一侧过大就右移；合法后直接计算中位数。'],
    '每个数组内部有序，所以只需两次交叉比较就能保证全部左区元素不大于右区。若 aLeft>bRight，第一数组左区过多，切分必须左移；反之必须右移。合法切分恰好保留所需半数元素，边界就是中位数位置。',
    'O(log(min(m,n)+1))', 'O(1)', ['0 ≤ 两个数组各自长度 ≤ 1000', '1 ≤ 总长度 ≤ 2000', '每个数组均非递减', '-10^6 ≤ 元素值 ≤ 10^6'],
    ['必须允许切分位置为 0 或数组长度。', '偶数情况下使用浮点除法，C++ 先转浮点避免加法溢出。']),
]
