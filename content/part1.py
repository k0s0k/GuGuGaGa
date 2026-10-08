"""原创 Hot 100 教学内容：哈希、数组、窗口、矩阵和链表。"""
from textwrap import dedent


def problem(id, title, slug, difficulty, category, summary, constraints, examples,
            method, params, returns, python, cpp, approach, steps, correctness,
            pitfalls, time, space, **extra):
    return dict(id=id, title=title, slug=slug, difficulty=difficulty, category=category,
                summary=summary, constraints=constraints,
                examples=[dict(input=i, output=o, explanation=e) for i, o, e in examples],
                method=method, params=[dict(name=n, type=t) for n, t in params],
                returns=returns, python=dedent(python).strip(), cpp=dedent(cpp).strip(),
                approach=approach, steps=steps, correctness=correctness,
                pitfalls=pitfalls, time=time, space=space, **extra)


PROBLEMS = [
    problem(1, '两数之和', 'two-sum', '简单', '哈希表',
        '给定整数数组 nums 和目标值 target，返回两个不同下标，使对应数值之和等于 target。题目保证恰有一组答案，下标顺序不限。',
        ['2 ≤ nums.length ≤ 10⁴', '数值与 target 均在 [-10⁹, 10⁹] 内', '不能重复使用同一个元素'],
        [([[2,7,11,15],9],[0,1],'2 + 7 = 9。'), ([[3,3],6],[0,1],'值可以相同，但必须来自不同下标。')],
        'twoSum', [('nums','int[]'),('target','int')], 'int[]',
        '''
        from typing import List

        class Solution:
            def twoSum(self, nums: List[int], target: int) -> List[int]:
                seen = {}
                for index, value in enumerate(nums):
                    complement = target - value
                    # 先查询再记录，保证不会重复使用当前元素。
                    if complement in seen:
                        return [seen[complement], index]
                    seen[value] = index
                return []
        ''', '''
        class Solution {
        public:
            vector<int> twoSum(vector<int>& nums, int target) {
                unordered_map<int, int> seen;
                for (int i = 0; i < (int)nums.size(); ++i) {
                    int need = target - nums[i];
                    // 仅匹配已经经过的下标。
                    if (seen.count(need)) return {seen[need], i};
                    seen[nums[i]] = i;
                }
                return {};
            }
        };
        ''', '用哈希表保存已出现数值的下标，一次遍历中寻找当前数的补数。',
        ['建立数值到下标的映射。','对当前数先查找 target - 当前数。','找到则返回两个下标，否则记录当前数。'],
        '遍历到答案中靠后的元素时，靠前元素已经存入哈希表，因此一定会被找到；先查询后写入保证两个下标不同。',
        ['不能先存入再查询，否则可能让一个元素和自己配对。','哈希表存下标，不只是是否出现。'], '平均 O(n)', 'O(n)', compare='unordered'),

    problem(49, '字母异位词分组', 'group-anagrams', '中等', '哈希表',
        '将字符串数组 strs 按字母异位词分组：同组字符串中每个字母出现的次数完全相同。返回所有分组，组间及组内顺序不限。',
        ['1 ≤ strs.length ≤ 10⁴', '0 ≤ 每个字符串长度 ≤ 100', '字符串仅含小写英文字母'],
        [([['eat','tea','tan','ate','nat','bat']],[['eat','tea','ate'],['tan','nat'],['bat']],'三种不同的字母计数形成三组。'), ([['','']], [['','']], '空字符串属于同一组。')],
        'groupAnagrams', [('strs','string[]')], 'string[][]',
        '''
        from typing import List
        from collections import defaultdict

        class Solution:
            def groupAnagrams(self, strs: List[str]) -> List[List[str]]:
                groups = defaultdict(list)
                for word in strs:
                    counts = [0] * 26
                    for letter in word:
                        counts[ord(letter) - ord('a')] += 1
                    # 元组可作为键，完整保留每个字母的次数。
                    groups[tuple(counts)].append(word)
                return list(groups.values())
        ''', '''
        class Solution {
        public:
            vector<vector<string>> groupAnagrams(vector<string>& strs) {
                unordered_map<string, vector<string>> groups;
                for (const string& word : strs) {
                    vector<int> counts(26, 0);
                    for (char c : word) ++counts[c - 'a'];
                    string key;
                    // 分隔符避免计数 1,11 与 11,1 混淆。
                    for (int count : counts) key += "#" + to_string(count);
                    groups[key].push_back(word);
                }
                vector<vector<string>> answer;
                for (auto& entry : groups) answer.push_back(move(entry.second));
                return answer;
            }
        };
        ''', '用 26 个字母的频次数组作为分组键，无需对每个单词排序。',
        ['统计单词中 26 个字母的出现次数。','将相同频次键的单词加入同一组。','返回哈希表中的所有分组。'],
        '两个单词可以通过重排互相转换，当且仅当每个字母出现的次数相同。频次键因此恰好刻画每一个分组。',
        ['空字符串的计数全部为零，也必须保留。','序列化计数时要使用分隔符。'], '平均 O(S + 26n)，S 为总字符数', 'O(S + 26n)，含输出', compare='groups'),

    problem(128, '最长连续序列', 'longest-consecutive-sequence', '中等', '哈希表',
        '在未排序整数数组 nums 中，求数值连续的最长序列长度。连续指相邻值差为 1，元素在原数组中的位置不必相邻。要求平均线性时间。',
        ['0 ≤ nums.length ≤ 10⁵', '-10⁹ ≤ nums[i] ≤ 10⁹', '重复值不增加序列长度'],
        [([[100,4,200,1,3,2]],4,'1、2、3、4 构成长为 4 的序列。'), ([[]],0,'空数组没有连续序列。'), ([[1,2,2,3]],3,'重复的 2 只计算一次。')],
        'longestConsecutive', [('nums','int[]')], 'int',
        '''
        from typing import List

        class Solution:
            def longestConsecutive(self, nums: List[int]) -> int:
                values = set(nums)
                longest = 0
                for value in values:
                    # 只从没有前驱的序列起点向后数。
                    if value - 1 in values:
                        continue
                    end = value
                    while end + 1 in values:
                        end += 1
                    longest = max(longest, end - value + 1)
                return longest
        ''', '''
        class Solution {
        public:
            int longestConsecutive(vector<int>& nums) {
                unordered_set<int> values(nums.begin(), nums.end());
                int longest = 0;
                for (int value : values) {
                    if (values.count(value - 1)) continue;
                    int end = value;
                    // 每条连续段仅从最小值开始扫描一次。
                    while (values.count(end + 1)) ++end;
                    longest = max(longest, end - value + 1);
                }
                return longest;
            }
        };
        ''', '哈希集合去重，只从没有前驱的数开始扫描连续段。',
        ['把所有值放入集合。','若 x - 1 存在，跳过 x。','从真正的起点不断检查下一个整数并更新最长长度。'],
        '每个连续段有且只有一个不存在前驱的起点。扫描该起点会覆盖整段，其他元素不会重复发起扫描，所以所有段都被完整且仅一次地计算。',
        ['遍历去重后的集合，避免重复起点造成额外扫描。','不要对每个数都向后扫描。'], '平均 O(n)', 'O(n)'),

    problem(283, '移动零', 'move-zeroes', '简单', '双指针',
        '原地将 nums 中所有 0 移到末尾，并保持非零元素的相对顺序。函数不返回数组，请直接修改输入。',
        ['1 ≤ nums.length ≤ 10⁴', '使用常数额外空间'],
        [([[0,1,0,3,12]],[1,3,12,0,0],'非零元素仍按 1、3、12 的顺序排列。'), ([[0]],[0],'只有一个零时保持不变。')],
        'moveZeroes', [('nums','int[]')], 'void',
        '''
        from typing import List

        class Solution:
            def moveZeroes(self, nums: List[int]) -> None:
                write = 0
                for read in range(len(nums)):
                    if nums[read] != 0:
                        # write 左侧始终是已经排好的非零元素。
                        nums[write], nums[read] = nums[read], nums[write]
                        write += 1
        ''', '''
        class Solution {
        public:
            void moveZeroes(vector<int>& nums) {
                int write = 0;
                for (int read = 0; read < (int)nums.size(); ++read) {
                    if (nums[read] != 0) {
                        // 顺序扫描并依次放入非零区域。
                        swap(nums[write], nums[read]);
                        ++write;
                    }
                }
            }
        };
        ''', '快指针扫描，慢指针标记下一个非零元素应放入的位置。',
        ['令 write 指向数组开头。','扫描到非零值时与 write 位置交换。','将 write 向右移动，继续扫描。'],
        '每次交换都把下一个非零值放到已处理非零区间的末尾，因此相对顺序不变。扫描结束后其余位置只能是零。',
        ['只有遇到非零元素时才移动 write。','必须修改 nums 本身。'], 'O(n)', 'O(1)', mutates=0),

    problem(11, '盛最多水的容器', 'container-with-most-water', '中等', '双指针',
        '数组 height[i] 表示横坐标 i 处竖线的高度。选择两条线与横轴组成容器，返回最多可容纳的面积；容器不能倾斜。',
        ['2 ≤ height.length ≤ 10⁵', '0 ≤ height[i] ≤ 10⁴'],
        [([[1,8,6,2,5,4,8,3,7]],49,'下标 1 与 8 之间宽度 7、较低高度 7。'), ([[1,1]],1,'两条等高线组成面积为 1 的容器。')],
        'maxArea', [('height','int[]')], 'int',
        '''
        from typing import List

        class Solution:
            def maxArea(self, height: List[int]) -> int:
                left, right = 0, len(height) - 1
                best = 0
                while left < right:
                    best = max(best, (right - left) * min(height[left], height[right]))
                    # 短板不换，宽度缩小后面积不可能变大。
                    if height[left] <= height[right]:
                        left += 1
                    else:
                        right -= 1
                return best
        ''', '''
        class Solution {
        public:
            int maxArea(vector<int>& height) {
                int left = 0, right = (int)height.size() - 1, best = 0;
                while (left < right) {
                    best = max(best, (right - left) * min(height[left], height[right]));
                    // 只淘汰较短的一端。
                    if (height[left] <= height[right]) ++left;
                    else --right;
                }
                return best;
            }
        };
        ''', '从最宽的两端出发，每次记录面积并移动较短的那条线。',
        ['左右指针指向两端。','用宽度乘两端较低高度更新答案。','移动较短的一端，直到两指针相遇。'],
        '若左端较短，固定左端并向左移动右端只会缩小宽度，水面高度也不可能超过左端。因此所有尚未考察且包含该左端的容器都不更优，可以安全舍弃它。',
        ['面积使用较低高度，不是较高高度。','宽度为 right - left。'], 'O(n)', 'O(1)'),

    problem(15, '三数之和', '3sum', '中等', '双指针',
        '返回 nums 中所有和为 0 的三元组。每组必须使用三个不同下标，结果不能包含数值相同的重复三元组，输出顺序不限。',
        ['3 ≤ nums.length ≤ 3000', '-10⁵ ≤ nums[i] ≤ 10⁵'],
        [([[-1,0,1,2,-1,-4]],[[-1,-1,2],[-1,0,1]],'相同数值组合只保留一次。'), ([[0,0,0,0]],[[0,0,0]],'四个零只对应一个不同三元组。')],
        'threeSum', [('nums','int[]')], 'int[][]',
        '''
        from typing import List

        class Solution:
            def threeSum(self, nums: List[int]) -> List[List[int]]:
                nums.sort()
                answer = []
                for first in range(len(nums) - 2):
                    if nums[first] > 0:
                        break
                    if first > 0 and nums[first] == nums[first - 1]:
                        continue
                    left, right = first + 1, len(nums) - 1
                    while left < right:
                        total = nums[first] + nums[left] + nums[right]
                        if total < 0:
                            left += 1
                        elif total > 0:
                            right -= 1
                        else:
                            answer.append([nums[first], nums[left], nums[right]])
                            left += 1
                            right -= 1
                            # 同一次固定下标下，跳过已输出的两端数值。
                            while left < right and nums[left] == nums[left - 1]:
                                left += 1
                            while left < right and nums[right] == nums[right + 1]:
                                right -= 1
                return answer
        ''', '''
        class Solution {
        public:
            vector<vector<int>> threeSum(vector<int>& nums) {
                sort(nums.begin(), nums.end());
                vector<vector<int>> answer;
                int n = nums.size();
                for (int first = 0; first + 2 < n; ++first) {
                    if (nums[first] > 0) break;
                    if (first > 0 && nums[first] == nums[first - 1]) continue;
                    int left = first + 1, right = n - 1;
                    while (left < right) {
                        int total = nums[first] + nums[left] + nums[right];
                        if (total < 0) ++left;
                        else if (total > 0) --right;
                        else {
                            answer.push_back({nums[first], nums[left], nums[right]});
                            ++left;
                            --right;
                            // 去重只跳过相同数值，不跳过新的候选值。
                            while (left < right && nums[left] == nums[left - 1]) ++left;
                            while (left < right && nums[right] == nums[right + 1]) --right;
                        }
                    }
                }
                return answer;
            }
        };
        ''', '排序后固定第一个数，用相向双指针寻找剩余两数，并在三处去重。',
        ['排序，使两数之和随指针移动具有单调性。','固定每个不同的第一个数。','和偏小时左指针右移，偏大时右指针左移。','找到答案后移动两端并跳过重复数值。'],
        '固定第一个数后，若当前和过小，所有使用当前左值及更小右值的组合都过小，可以舍弃左值；和过大同理。枚举所有不同首值即可覆盖全部答案，跳过重复值只去除相同组合。',
        ['去重比较必须与已经处理的值进行。','三个下标通过 first < left < right 保证不同。'], 'O(n²)', 'Python 排序 O(n)，C++ 排序 O(log n)，均不计输出', compare='groups'),

    problem(42, '接雨水', 'trapping-rain-water', '困难', '双指针',
        'height 描述宽度均为 1 的柱子高度。雨水停留在柱子之间，返回降雨后能够积存的总水量。',
        ['1 ≤ height.length ≤ 2 × 10⁴', '0 ≤ height[i] ≤ 10⁵'],
        [([[0,1,0,2,1,0,1,3,2,1,2,1]],6,'各低洼位置的蓄水量相加得到 6。'), ([[3,3,3]],0,'没有低洼位置。')],
        'trap', [('height','int[]')], 'int',
        '''
        from typing import List

        class Solution:
            def trap(self, height: List[int]) -> int:
                left, right = 0, len(height) - 1
                left_max = right_max = water = 0
                while left <= right:
                    left_max = max(left_max, height[left])
                    right_max = max(right_max, height[right])
                    # 较低一侧的最高墙已决定该侧水位。
                    if left_max <= right_max:
                        water += left_max - height[left]
                        left += 1
                    else:
                        water += right_max - height[right]
                        right -= 1
                return water
        ''', '''
        class Solution {
        public:
            int trap(vector<int>& height) {
                int left = 0, right = (int)height.size() - 1;
                int leftMax = 0, rightMax = 0, water = 0;
                while (left <= right) {
                    leftMax = max(leftMax, height[left]);
                    rightMax = max(rightMax, height[right]);
                    // 另一侧已有足够高的边界，可以结算较低的一侧。
                    if (leftMax <= rightMax) water += leftMax - height[left++];
                    else water += rightMax - height[right--];
                }
                return water;
            }
        };
        ''', '维护两端已见最高墙，每次结算最高墙较低一侧的蓄水量。',
        ['左右指针从两端向中间移动。','更新左右两侧最高墙。','较低最高墙对应一侧的水量已经确定，累加后移动该侧。'],
        '当 left_max ≤ right_max 时，左指针右边至少有 right_max 这么高的墙，左边最高墙又恰为 left_max，因此该位置水位必为 left_max。对另一侧同理，所有位置各结算一次。',
        ['必须先更新最高墙再计算水量。','雨水量按每个位置累加，不能直接用两端组成的大矩形。'], 'O(n)', 'O(1)'),

    problem(3, '无重复字符的最长子串', 'longest-substring-without-repeating-characters', '中等', '滑动窗口',
        '返回字符串 s 中不含重复字符的最长连续子串长度。子串必须连续，空字符串的答案为 0。',
        ['0 ≤ s.length ≤ 5 × 10⁴', '字符可为英文字母、数字、符号或空格'],
        [(['abcabcbb'],3,'abc 是一个最长合法子串。'), ([''],0,'空串没有字符。'), (['abba'],2,'遇到旧位置时左边界不能倒退。')],
        'lengthOfLongestSubstring', [('s','string')], 'int',
        '''
        class Solution:
            def lengthOfLongestSubstring(self, s: str) -> int:
                last = {}
                left = best = 0
                for right, char in enumerate(s):
                    # 已经滑出窗口的重复字符不会让 left 回退。
                    left = max(left, last.get(char, -1) + 1)
                    last[char] = right
                    best = max(best, right - left + 1)
                return best
        ''', '''
        class Solution {
        public:
            int lengthOfLongestSubstring(string s) {
                vector<int> last(256, -1);
                int left = 0, best = 0;
                for (int right = 0; right < (int)s.size(); ++right) {
                    unsigned char c = s[right];
                    // unsigned char 避免字符作为下标时出现负数。
                    left = max(left, last[c] + 1);
                    last[c] = right;
                    best = max(best, right - left + 1);
                }
                return best;
            }
        };
        ''', '滑动窗口结合字符最后出现位置，使左边界直接跳过重复字符。',
        ['记录每个字符最近一次出现的位置。','右端加入字符，必要时将左端跳到上次出现位置之后。','更新窗口长度的最大值。'],
        '每次左边界调整后，当前字符在窗口中只出现一次，其他字符仍不重复。左边界取满足条件的最小值，因此当前窗口是以 right 结尾的最长合法子串。',
        ['left 必须取 max，不能直接覆盖。','题目求子串，不是子序列。'], 'O(n)', 'O(|Σ|)，Σ 为字符集'),

    problem(438, '找到字符串中所有字母异位词', 'find-all-anagrams-in-a-string', '中等', '滑动窗口',
        '返回 s 中所有长度与 p 相同、且字母出现次数与 p 完全相同的子串起始下标。返回下标按升序排列。',
        ['1 ≤ s.length, p.length ≤ 3 × 10⁴', '仅包含小写英文字母'],
        [(['cbaebabacd','abc'],[0,6],'cba 与 bac 都是 abc 的异位词。'), (['a','ab'],[],'s 比 p 短，不存在合法窗口。')],
        'findAnagrams', [('s','string'),('p','string')], 'int[]',
        '''
        from typing import List

        class Solution:
            def findAnagrams(self, s: str, p: str) -> List[int]:
                need = [0] * 26
                window = [0] * 26
                for char in p:
                    need[ord(char) - ord('a')] += 1
                answer = []
                width = len(p)
                for right, char in enumerate(s):
                    window[ord(char) - ord('a')] += 1
                    if right >= width:
                        window[ord(s[right - width]) - ord('a')] -= 1
                    # 字母表固定为 26，比较计数是常数时间。
                    if right + 1 >= width and window == need:
                        answer.append(right - width + 1)
                return answer
        ''', '''
        class Solution {
        public:
            vector<int> findAnagrams(string s, string p) {
                vector<int> need(26, 0), window(26, 0), answer;
                for (char c : p) ++need[c - 'a'];
                int width = p.size();
                for (int right = 0; right < (int)s.size(); ++right) {
                    ++window[s[right] - 'a'];
                    if (right >= width) --window[s[right - width] - 'a'];
                    // 仅在窗口已经达到目标长度时判断。
                    if (right + 1 >= width && window == need)
                        answer.push_back(right - width + 1);
                }
                return answer;
            }
        };
        ''', '用长度固定为 |p| 的窗口维护 26 个字母计数。',
        ['统计 p 的字母频次。','右侧加入一个字符，超过固定宽度时移除左侧字符。','窗口长度足够且计数相同时记录起点。'],
        '所有候选子串都具有长度 |p|，滑动窗口按顺序枚举了全部候选。字母频次完全相同等价于异位词，因此判断既不遗漏也不误报。',
        ['移出窗口的下标是 right - width。','窗口未形成时不能记录答案。'], 'O(|s| + |p|)，字母表固定为 26', 'O(1)，不计输出'),

    problem(560, '和为 K 的子数组', 'subarray-sum-equals-k', '中等', '前缀和',
        '给定整数数组 nums 和整数 k，统计元素和等于 k 的非空连续子数组个数。数组可能包含负数和零。',
        ['1 ≤ nums.length ≤ 2 × 10⁴', '-1000 ≤ nums[i] ≤ 1000', '-10⁷ ≤ k ≤ 10⁷'],
        [([[1,1,1],2],2,'下标区间 [0,1] 和 [1,2] 满足要求。'), ([[0,0],0],3,'两个单元素子数组与整个数组都满足要求。')],
        'subarraySum', [('nums','int[]'),('k','int')], 'int',
        '''
        from typing import List

        class Solution:
            def subarraySum(self, nums: List[int], k: int) -> int:
                frequencies = {0: 1}
                prefix = answer = 0
                for value in nums:
                    prefix += value
                    # 只统计之前出现的前缀，保证子数组非空。
                    answer += frequencies.get(prefix - k, 0)
                    frequencies[prefix] = frequencies.get(prefix, 0) + 1
                return answer
        ''', '''
        class Solution {
        public:
            int subarraySum(vector<int>& nums, int k) {
                unordered_map<int, int> frequencies;
                frequencies[0] = 1; // 空前缀允许子数组从下标 0 开始。
                int prefix = 0, answer = 0;
                for (int value : nums) {
                    prefix += value;
                    auto it = frequencies.find(prefix - k);
                    if (it != frequencies.end()) answer += it->second;
                    ++frequencies[prefix];
                }
                return answer;
            }
        };
        ''', '子数组和等于两个前缀和之差，用哈希表累计每种前缀和出现的次数。',
        ['初始化空前缀和 0 出现一次。','累加当前前缀和 prefix。','把此前 prefix - k 的出现次数加入答案，再记录当前前缀和。'],
        '以当前位置结尾的子数组和为 k，当且仅当它之前的前缀和为 prefix - k。频次表记录了所有可能左端点，每个子数组只会在其右端点处理一次。',
        ['负数使普通滑动窗口失去单调性。','必须累计次数，不能只存是否出现。','先查询后更新可避免把空子数组计入。'], '平均 O(n)', 'O(n)'),

    problem(239, '滑动窗口最大值', 'sliding-window-maximum', '困难', '单调队列',
        '宽度为 k 的窗口从 nums 左端逐格向右滑动。返回每个完整窗口中的最大值，顺序与窗口出现顺序一致。',
        ['1 ≤ k ≤ nums.length ≤ 10⁵', '-10⁴ ≤ nums[i] ≤ 10⁴'],
        [([[1,3,-1,-3,5,3,6,7],3],[3,3,5,5,6,7],'共有 6 个长度为 3 的窗口。'), ([[4,2],1],[4,2],'宽度为 1 时每个元素就是窗口最大值。')],
        'maxSlidingWindow', [('nums','int[]'),('k','int')], 'int[]',
        '''
        from typing import List
        from collections import deque

        class Solution:
            def maxSlidingWindow(self, nums: List[int], k: int) -> List[int]:
                candidates = deque()
                answer = []
                for right, value in enumerate(nums):
                    if candidates and candidates[0] <= right - k:
                        candidates.popleft()
                    # 较旧且不更大的值永远不可能优于当前值。
                    while candidates and nums[candidates[-1]] <= value:
                        candidates.pop()
                    candidates.append(right)
                    if right >= k - 1:
                        answer.append(nums[candidates[0]])
                return answer
        ''', '''
        class Solution {
        public:
            vector<int> maxSlidingWindow(vector<int>& nums, int k) {
                deque<int> candidates;
                vector<int> answer;
                for (int right = 0; right < (int)nums.size(); ++right) {
                    if (!candidates.empty() && candidates.front() <= right - k)
                        candidates.pop_front();
                    // 队列存下标，对应数值严格递减。
                    while (!candidates.empty() && nums[candidates.back()] <= nums[right])
                        candidates.pop_back();
                    candidates.push_back(right);
                    if (right >= k - 1) answer.push_back(nums[candidates.front()]);
                }
                return answer;
            }
        };
        ''', '维护数值递减的下标队列，队首就是当前窗口最大值。',
        ['移除已经离开窗口的队首。','从队尾移除不大于当前值的候选。','当前下标入队，完整窗口形成后读取队首。'],
        '若旧元素不大于新元素，新元素更大且更晚过期，旧元素在未来窗口中不再可能成为必要的最大值候选。保留的候选按值递减，队首即最大值。每个下标至多入队、出队一次。',
        ['队列存下标才能判断元素是否过期。','输出从 right = k - 1 开始。'], 'O(n)', 'O(k)，不计输出'),

    problem(76, '最小覆盖子串', 'minimum-window-substring', '困难', '滑动窗口',
        '在字符串 s 中寻找最短连续子串，使它包含 t 中的每个字符且次数不少于 t 中对应次数。若不存在则返回空串；题目保证最短答案唯一。',
        ['1 ≤ s.length, t.length ≤ 10⁵', '字符串由大小写英文字母组成', '大小写视为不同字符'],
        [(['ADOBECODEBANC','ABC'],'BANC','BANC 包含 A、B、C，且不存在更短覆盖。'), (['a','aa'],'','一个 a 不能满足两个 a 的需求。')],
        'minWindow', [('s','string'),('t','string')], 'string',
        '''
        from collections import Counter

        class Solution:
            def minWindow(self, s: str, t: str) -> str:
                need = Counter(t)
                missing = len(t)
                left = best_start = 0
                best_length = len(s) + 1
                for right, char in enumerate(s):
                    if need[char] > 0:
                        missing -= 1
                    need[char] -= 1
                    # 满足覆盖后尽量收缩，寻找以 right 结尾的最短窗口。
                    while missing == 0:
                        if right - left + 1 < best_length:
                            best_start, best_length = left, right - left + 1
                        removed = s[left]
                        need[removed] += 1
                        if need[removed] > 0:
                            missing += 1
                        left += 1
                return '' if best_length > len(s) else s[best_start:best_start + best_length]
        ''', '''
        class Solution {
        public:
            string minWindow(string s, string t) {
                vector<int> need(128, 0);
                for (char c : t) ++need[c];
                int missing = t.size(), left = 0, bestStart = 0;
                int bestLength = (int)s.size() + 1;
                for (int right = 0; right < (int)s.size(); ++right) {
                    if (need[s[right]] > 0) --missing;
                    --need[s[right]];
                    while (missing == 0) {
                        if (right - left + 1 < bestLength) {
                            bestStart = left;
                            bestLength = right - left + 1;
                        }
                        // 移走一个真正需要的字符后，窗口重新变为不合法。
                        if (++need[s[left]] > 0) ++missing;
                        ++left;
                    }
                }
                return bestLength > (int)s.size() ? "" : s.substr(bestStart, bestLength);
            }
        };
        ''', '用缺失字符总数判断是否覆盖，右端扩展满足条件后连续收缩左端。',
        ['记录 t 的频次，missing 初始化为 |t|。','加入右端字符，只有填补需求时才减少 missing。','missing 为 0 时记录答案并不断移出左端字符。','窗口重新缺少字符后继续扩展右端。'],
        'need 维护目标频次与窗口频次之差，missing 为所有正差之和，所以 missing = 0 等价于完整覆盖。每个右端点都收缩到最短合法窗口，比较这些候选即可得到全局最短。',
        ['重复字符必须按次数满足，不能只比较字符种类。','need 为负表示当前字符有富余。'], 'O(|s| + |t|)', 'O(|Σ|)，Σ 为字符集'),
]


PROBLEMS.extend([
    problem(53, '最大子数组和', 'maximum-subarray', '中等', '动态规划',
        '在 nums 中选择一个非空连续子数组，返回可取得的最大元素和。即使所有元素均为负数，也必须选择至少一个元素。',
        ['1 ≤ nums.length ≤ 10⁵', '-10⁴ ≤ nums[i] ≤ 10⁴'],
        [([[-2,1,-3,4,-1,2,1,-5,4]],6,'子数组 [4,-1,2,1] 的和为 6。'), ([[-5,-2,-9]],-2,'全部为负数时选择最大的单个元素。')],
        'maxSubArray', [('nums','int[]')], 'int',
        '''
        from typing import List

        class Solution:
            def maxSubArray(self, nums: List[int]) -> int:
                ending = best = nums[0]
                for index in range(1, len(nums)):
                    value = nums[index]
                    # 以当前数结尾：接在前段后面，或从自己重新开始。
                    ending = max(value, ending + value)
                    best = max(best, ending)
                return best
        ''', '''
        class Solution {
        public:
            int maxSubArray(vector<int>& nums) {
                int ending = nums[0], best = nums[0];
                for (int i = 1; i < (int)nums.size(); ++i) {
                    // ending 只描述必须以当前位置结尾的子数组。
                    ending = max(nums[i], ending + nums[i]);
                    best = max(best, ending);
                }
                return best;
            }
        };
        ''', '动态规划维护以当前位置结尾的最大和，并同时维护全局最大和。',
        ['用第一个元素初始化状态，确保子数组非空。','判断当前元素应接续之前的子数组还是独立开始。','用每个位置的结尾最优值更新全局答案。'],
        '以当前位置结尾的子数组，要么只含当前元素，要么由前一位置结尾的子数组追加当前元素得到。追加同一个值时只需保留前一位置的最大和，因此转移穷尽且选择了所有可能中的最优项。',
        ['不能把答案初始化成 0，否则全负数组会出错。','ending 与 best 含义不同，不能混用。'], 'O(n)', 'O(1)'),

    problem(56, '合并区间', 'merge-intervals', '中等', '贪心',
        '给定若干闭区间 intervals，将所有有重叠的区间合并，返回按起点升序排列且互不重叠的区间。端点相同也视为重叠。',
        ['1 ≤ intervals.length ≤ 10⁴', '0 ≤ start ≤ end ≤ 10⁴'],
        [([[[1,3],[2,6],[8,10],[15,18]]],[[1,6],[8,10],[15,18]],'前两个区间重叠，合并成 [1,6]。'), ([[[1,4],[4,5]]],[[1,5]],'闭区间在端点 4 相交。')],
        'merge', [('intervals','int[][]')], 'int[][]',
        '''
        from typing import List

        class Solution:
            def merge(self, intervals: List[List[int]]) -> List[List[int]]:
                intervals.sort(key=lambda interval: interval[0])
                merged = []
                for start, end in intervals:
                    if not merged or start > merged[-1][1]:
                        merged.append([start, end])
                    else:
                        # 当前起点落在最后区间内，只需扩大右端点。
                        merged[-1][1] = max(merged[-1][1], end)
                return merged
        ''', '''
        class Solution {
        public:
            vector<vector<int>> merge(vector<vector<int>>& intervals) {
                sort(intervals.begin(), intervals.end());
                vector<vector<int>> merged;
                for (const auto& interval : intervals) {
                    if (merged.empty() || interval[0] > merged.back()[1]) {
                        merged.push_back(interval);
                    } else {
                        // 被包含的区间不会使右端点变小。
                        merged.back()[1] = max(merged.back()[1], interval[1]);
                    }
                }
                return merged;
            }
        };
        ''', '按左端点排序后扫描，只需判断当前区间能否并入最后一个已合并区间。',
        ['按起点排序。','起点大于上一段终点时，新建一个结果区间。','否则把上一段终点更新为两者终点的最大值。'],
        '排序保证后续区间起点不小于当前区间。若当前起点已超过结果最后一段终点，它不可能与更早区间重叠；否则两段重叠，合并后仍完整覆盖相同点集。',
        ['相接端点也需要合并，因此分离条件为严格大于。','更新右端点取 max，不能直接覆盖。'], 'O(n log n)', 'O(n)，含结果'),

    problem(189, '轮转数组', 'rotate-array', '中等', '数组',
        '将 nums 中每个元素向右移动 k 个位置，越过末尾的元素回到开头。原地修改数组，不返回新数组。',
        ['1 ≤ nums.length ≤ 10⁵', '0 ≤ k ≤ 10⁵', '使用常数额外空间'],
        [([[1,2,3,4,5,6,7],3],[5,6,7,1,2,3,4],'末尾三个数移动到开头。'), ([[1,2],4],[1,2],'移动整整两圈后数组不变。')],
        'rotate', [('nums','int[]'),('k','int')], 'void',
        '''
        from typing import List

        class Solution:
            def rotate(self, nums: List[int], k: int) -> None:
                def reverse(left: int, right: int) -> None:
                    while left < right:
                        nums[left], nums[right] = nums[right], nums[left]
                        left += 1
                        right -= 1

                k %= len(nums)
                # 整体翻转交换两段位置，再分别恢复每段内部顺序。
                reverse(0, len(nums) - 1)
                reverse(0, k - 1)
                reverse(k, len(nums) - 1)
        ''', '''
        class Solution {
        public:
            void rotate(vector<int>& nums, int k) {
                k %= nums.size();
                // AB 整体反转成为 reverse(B)reverse(A)。
                reverse(nums.begin(), nums.end());
                reverse(nums.begin(), nums.begin() + k);
                reverse(nums.begin() + k, nums.end());
            }
        };
        ''', '将原数组看成 A、B 两段，三次翻转在常数空间内将 AB 变为 BA。',
        ['k 对数组长度取余。','翻转整个数组。','翻转前 k 个元素，再翻转剩余元素。'],
        '若 B 是长度为 k 的后缀，整体反转得到 reverse(B) + reverse(A)。分别翻转两段后恰为 B + A，即右移 k 位的结果。',
        ['先对 k 取余，避免移动超过一圈。','Python 不用切片反转，才能保持常数额外空间。'], 'O(n)', 'O(1)', mutates=0),

    problem(238, '除自身以外数组的乘积', 'product-of-array-except-self', '中等', '前缀和',
        '返回 answer，其中 answer[i] 等于 nums 中除 nums[i] 外所有元素的乘积。不得使用除法，要求线性时间。结果数组不计入额外空间。',
        ['2 ≤ nums.length ≤ 10⁵', '-30 ≤ nums[i] ≤ 30', '任意前缀、后缀及答案乘积均在 32 位有符号整数范围内'],
        [([[1,2,3,4]],[24,12,8,6],'每个位置乘上其余三个数。'), ([[-1,1,0,-3,3]],[0,0,9,0,0],'只有原来为零的位置能得到非零乘积。')],
        'productExceptSelf', [('nums','int[]')], 'int[]',
        '''
        from typing import List

        class Solution:
            def productExceptSelf(self, nums: List[int]) -> List[int]:
                answer = [1] * len(nums)
                for index in range(1, len(nums)):
                    answer[index] = answer[index - 1] * nums[index - 1]
                suffix = 1
                for index in range(len(nums) - 1, -1, -1):
                    # answer 已存左侧乘积，suffix 是严格右侧乘积。
                    answer[index] *= suffix
                    suffix *= nums[index]
                return answer
        ''', '''
        class Solution {
        public:
            vector<int> productExceptSelf(vector<int>& nums) {
                int n = nums.size();
                vector<int> answer(n, 1);
                for (int i = 1; i < n; ++i) answer[i] = answer[i - 1] * nums[i - 1];
                int suffix = 1;
                for (int i = n - 1; i >= 0; --i) {
                    // 先写答案，再把当前元素并入后缀积。
                    answer[i] *= suffix;
                    suffix *= nums[i];
                }
                return answer;
            }
        };
        ''', '每个答案等于严格左侧乘积乘严格右侧乘积，用结果数组保存前缀积，再用一个变量累计后缀积。',
        ['从左向右填写每个位置之前的乘积。','从右向左维护当前位置之后的乘积。','把两部分相乘得到当前答案。'],
        '除去自身后，其余元素被唯一分为左侧与右侧。第一轮和第二轮分别计算这两组乘积，二者相乘恰好包含每个其他元素一次。该分解对零和负数同样成立。',
        ['前缀和后缀均不能包含当前位置。','不能通过总乘积做除法，否则零元素也会造成问题。'], 'O(n)', 'O(1)，不计结果数组'),

    problem(41, '缺失的第一个正数', 'first-missing-positive', '困难', '数组',
        '返回 nums 中没有出现的最小正整数。要求 O(n) 时间和 O(1) 额外空间，允许修改数组内容。',
        ['1 ≤ nums.length ≤ 10⁵', '元素在 32 位有符号整数范围内'],
        [([[3,4,-1,1]],2,'1 已出现，2 未出现。'), ([[1,2,3]],4,'1 到 n 全部出现时答案为 n + 1。'), ([[1,1]],2,'重复值不能形成无限交换。')],
        'firstMissingPositive', [('nums','int[]')], 'int',
        '''
        from typing import List

        class Solution:
            def firstMissingPositive(self, nums: List[int]) -> int:
                size = len(nums)
                for index in range(size):
                    # 数值 x 的固定位置是 x - 1，重复值无需再次交换。
                    while 1 <= nums[index] <= size and nums[nums[index] - 1] != nums[index]:
                        target = nums[index] - 1
                        nums[index], nums[target] = nums[target], nums[index]
                for index, value in enumerate(nums):
                    if value != index + 1:
                        return index + 1
                return size + 1
        ''', '''
        class Solution {
        public:
            int firstMissingPositive(vector<int>& nums) {
                int n = nums.size();
                for (int i = 0; i < n; ++i) {
                    while (nums[i] >= 1 && nums[i] <= n && nums[nums[i] - 1] != nums[i]) {
                        // 每次交换都让至少一个有效值回到固定位置。
                        swap(nums[i], nums[nums[i] - 1]);
                    }
                }
                for (int i = 0; i < n; ++i) if (nums[i] != i + 1) return i + 1;
                return n + 1;
            }
        };
        ''', '将数组本身当作位置表，把范围 [1,n] 内的值 x 放到下标 x - 1。',
        ['扫描数组，不断把当前位置的有效值交换到它应该在的位置。','目标已经是相同值时停止，避免重复值循环。','再次扫描，第一个数值不匹配的位置就是缺失答案。'],
        '最小缺失正数必在 [1,n+1] 内。每次交换让一个有效值进入自己的唯一位置，已经归位的值不会再被换走，因此至多进行 n 次有效归位。最终 x 出现当且仅当位置 x - 1 存在 x。',
        ['访问 nums[value - 1] 前先检查值域。','目标位置已有相同值时必须停止。','Python 先保存 target，避免赋值求值顺序干扰。'], 'O(n)', 'O(1)'),

    problem(73, '矩阵置零', 'set-matrix-zeroes', '中等', '矩阵',
        '若 m × n 矩阵中的某个原始元素为 0，将它所在的整行和整列都置为 0。要求原地修改矩阵并使用常数额外空间。',
        ['1 ≤ m,n ≤ 200', '矩阵为非空矩形', '元素在 32 位有符号整数范围内'],
        [([[[1,1,1],[1,0,1],[1,1,1]]],[[1,0,1],[0,0,0],[1,0,1]],'中间的零影响第二行和第二列。'), ([[[0,1]]],[[0,0]],'只有一行时，该行的零使整行置零。')],
        'setZeroes', [('matrix','int[][]')], 'void',
        '''
        from typing import List

        class Solution:
            def setZeroes(self, matrix: List[List[int]]) -> None:
                rows, cols = len(matrix), len(matrix[0])
                first_row_zero = any(matrix[0][col] == 0 for col in range(cols))
                first_col_zero = any(matrix[row][0] == 0 for row in range(rows))
                for row in range(1, rows):
                    for col in range(1, cols):
                        if matrix[row][col] == 0:
                            # 首列记录行标记，首行记录列标记。
                            matrix[row][0] = matrix[0][col] = 0
                for row in range(1, rows):
                    for col in range(1, cols):
                        if matrix[row][0] == 0 or matrix[0][col] == 0:
                            matrix[row][col] = 0
                if first_row_zero:
                    for col in range(cols):
                        matrix[0][col] = 0
                if first_col_zero:
                    for row in range(rows):
                        matrix[row][0] = 0
        ''', '''
        class Solution {
        public:
            void setZeroes(vector<vector<int>>& matrix) {
                int rows = matrix.size(), cols = matrix[0].size();
                bool firstRowZero = false, firstColZero = false;
                for (int col = 0; col < cols; ++col) if (matrix[0][col] == 0) firstRowZero = true;
                for (int row = 0; row < rows; ++row) if (matrix[row][0] == 0) firstColZero = true;
                for (int row = 1; row < rows; ++row)
                    for (int col = 1; col < cols; ++col)
                        if (matrix[row][col] == 0) matrix[row][0] = matrix[0][col] = 0;
                // 标记全部完成后再修改内部区域。
                for (int row = 1; row < rows; ++row)
                    for (int col = 1; col < cols; ++col)
                        if (matrix[row][0] == 0 || matrix[0][col] == 0) matrix[row][col] = 0;
                if (firstRowZero) for (int col = 0; col < cols; ++col) matrix[0][col] = 0;
                if (firstColZero) for (int row = 0; row < rows; ++row) matrix[row][0] = 0;
            }
        };
        ''', '复用矩阵第一行和第一列存储置零标记，额外用两个布尔值保存它们自身的原始状态。',
        ['记录首行、首列原本是否有零。','扫描内部元素，在首行首列写入相应标记。','依据标记清零内部区域。','最后处理首行和首列。'],
        '内部元素的原始零会在对应行首和列首留下标记，首行首列原始零也天然提供相应标记。因此第二轮准确清零所有受影响内部元素。两个布尔值避免标记操作污染首行首列自身的判断。',
        ['发现零就立即清整行整列会让新增零继续传播。','首行首列必须最后处理。'], 'O(mn)', 'O(1)', mutates=0),

    problem(54, '螺旋矩阵', 'spiral-matrix', '中等', '矩阵',
        '从矩阵左上角出发，依次向右、向下、向左、向上，逐层向内按顺时针螺旋顺序读取所有元素，返回读取序列。',
        ['1 ≤ m,n ≤ 10', '矩阵为非空矩形'],
        [([[[1,2,3],[4,5,6],[7,8,9]]],[1,2,3,6,9,8,7,4,5],'先遍历外圈，再读取中心。'), ([[[1],[2],[3]]],[1,2,3],'只有一列时每个元素仅访问一次。')],
        'spiralOrder', [('matrix','int[][]')], 'int[]',
        '''
        from typing import List

        class Solution:
            def spiralOrder(self, matrix: List[List[int]]) -> List[int]:
                top, bottom = 0, len(matrix) - 1
                left, right = 0, len(matrix[0]) - 1
                answer = []
                while top <= bottom and left <= right:
                    for col in range(left, right + 1):
                        answer.append(matrix[top][col])
                    top += 1
                    for row in range(top, bottom + 1):
                        answer.append(matrix[row][right])
                    right -= 1
                    # 剩余区域必须仍有效，才能遍历下面和左面。
                    if top <= bottom:
                        for col in range(right, left - 1, -1):
                            answer.append(matrix[bottom][col])
                        bottom -= 1
                    if left <= right:
                        for row in range(bottom, top - 1, -1):
                            answer.append(matrix[row][left])
                        left += 1
                return answer
        ''', '''
        class Solution {
        public:
            vector<int> spiralOrder(vector<vector<int>>& matrix) {
                int top = 0, bottom = (int)matrix.size() - 1;
                int left = 0, right = (int)matrix[0].size() - 1;
                vector<int> answer;
                while (top <= bottom && left <= right) {
                    for (int col = left; col <= right; ++col) answer.push_back(matrix[top][col]);
                    ++top;
                    for (int row = top; row <= bottom; ++row) answer.push_back(matrix[row][right]);
                    --right;
                    // 收缩边界后检查，避免重复读取单行或单列。
                    if (top <= bottom) {
                        for (int col = right; col >= left; --col) answer.push_back(matrix[bottom][col]);
                        --bottom;
                    }
                    if (left <= right) {
                        for (int row = bottom; row >= top; --row) answer.push_back(matrix[row][left]);
                        ++left;
                    }
                }
                return answer;
            }
        };
        ''', '四个边界围住尚未访问的矩形，每走完一条边就收缩对应边界。',
        ['按上、右、下、左的顺序读取边界。','读取一边后将对应边界向内缩进。','读取下边和左边前再次检查是否仍有剩余区域。'],
        '每次读取的是当前未访问矩形的一条边，随后将它从剩余区域中删除。边界检查防止读取空区域，所以每个元素恰好被读取一次，顺序符合顺时针螺旋。',
        ['单行或单列时，后两条边可能已经不存在。','读取右边时从更新后的 top 开始，避免重复角点。'], 'O(mn)', 'O(1)，不计输出'),

    problem(48, '旋转图像', 'rotate-image', '中等', '矩阵',
        '将 n × n 方阵顺时针旋转 90 度。必须原地修改 matrix，不能另建一个同尺寸矩阵。',
        ['1 ≤ n ≤ 20', 'matrix 为方阵'],
        [([[[1,2,3],[4,5,6],[7,8,9]]],[[7,4,1],[8,5,2],[9,6,3]],'原来的第一列变成新的第一行，且顺序反转。'), ([[[5]]],[[5]],'单个元素旋转后不变。')],
        'rotate', [('matrix','int[][]')], 'void',
        '''
        from typing import List

        class Solution:
            def rotate(self, matrix: List[List[int]]) -> None:
                size = len(matrix)
                for row in range(size):
                    for col in range(row + 1, size):
                        # 只交换主对角线一侧，完成转置。
                        matrix[row][col], matrix[col][row] = matrix[col][row], matrix[row][col]
                for row in matrix:
                    row.reverse()
        ''', '''
        class Solution {
        public:
            void rotate(vector<vector<int>>& matrix) {
                int n = matrix.size();
                for (int row = 0; row < n; ++row)
                    for (int col = row + 1; col < n; ++col)
                        swap(matrix[row][col], matrix[col][row]);
                // 转置后逐行反转，得到顺时针 90 度旋转。
                for (auto& row : matrix) reverse(row.begin(), row.end());
            }
        };
        ''', '先沿主对角线转置，再反转每一行。',
        ['交换所有 row < col 位置与其对称位置。','将每一行原地反转。'],
        '转置把位置 (r,c) 变成 (c,r)，逐行反转再把它变成 (c,n-1-r)，恰好是顺时针旋转 90 度的目标坐标。',
        ['转置只遍历对角线的一侧，否则会交换两次。','第二步是反转每一行，不是反转每一列。'], 'O(n²)', 'O(1)', mutates=0),

    problem(240, '搜索二维矩阵 II', 'search-a-2d-matrix-ii', '中等', '矩阵',
        '矩阵每行从左到右升序、每列从上到下升序。判断整数 target 是否在矩阵中出现。相邻两行之间不保证整体有序。',
        ['1 ≤ m,n ≤ 300', '每一行与每一列均按非降序排列'],
        [([[[1,4,7],[2,5,8],[3,6,9]],6],True,'目标位于最后一行第二列。'), ([[[1,2],[3,4]],5],False,'所有元素都小于目标。')],
        'searchMatrix', [('matrix','int[][]'),('target','int')], 'bool',
        '''
        from typing import List

        class Solution:
            def searchMatrix(self, matrix: List[List[int]], target: int) -> bool:
                row, col = 0, len(matrix[0]) - 1
                while row < len(matrix) and col >= 0:
                    value = matrix[row][col]
                    if value == target:
                        return True
                    if value > target:
                        col -= 1  # 当前列以下更大，整列都可排除。
                    else:
                        row += 1  # 当前行左侧更小，整行都可排除。
                return False
        ''', '''
        class Solution {
        public:
            bool searchMatrix(vector<vector<int>>& matrix, int target) {
                int row = 0, col = (int)matrix[0].size() - 1;
                while (row < (int)matrix.size() && col >= 0) {
                    if (matrix[row][col] == target) return true;
                    // 从右上角出发，每一步排除一整行或一整列。
                    if (matrix[row][col] > target) --col;
                    else ++row;
                }
                return false;
            }
        };
        ''', '从右上角做阶梯搜索：过大就向左，过小就向下。',
        ['定位当前剩余矩形的右上角。','等于目标时返回 true。','大于目标排除当前列，小于目标排除当前行。','越界后返回 false。'],
        '右上角是当前行最大值、当前列最小值。它比目标小则整行都过小；它比目标大则整列都过大。每次排除的部分不可能含目标，直到找到目标或候选区域为空。',
        ['该矩阵不能直接当成整体有序的一维数组。','从左上角开始无法根据一次比较确定排除方向。'], 'O(m+n)', 'O(1)'),
])


PROBLEMS.extend([
    problem(160, '相交链表', 'intersection-of-two-linked-lists', '简单', '链表',
        '给定两个无环单链表的头节点，返回它们第一次共享的节点；没有共享节点则返回 null。共享指同一个节点对象，数值相等不代表相交。练习输入为 [listA,listB,skipA,skipB]，两个 skip 指定共享后缀的起点；均为 -1 表示不相交。输出交点的值或 null。',
        ['每条链表节点数不超过 3 × 10⁴', '输入构造的两条链表无环', '不得改变原链表结构'],
        [([[4,1,8,4,5],[5,6,1,8,4,5],2,3],8,'两条链表从值为 8 的同一个节点开始共享后缀。'), ([[1,2],[3,2],-1,-1],None,'末尾的值虽然都为 2，但节点并不共享。')],
        'getIntersectionNode', [('headA','ListNode'),('headB','ListNode')], 'ListNode',
        '''
        from typing import Optional

        class Solution:
            def getIntersectionNode(self, headA: 'ListNode', headB: 'ListNode') -> Optional['ListNode']:
                first, second = headA, headB
                while first is not second:
                    # 走完自己的链表后换到另一条，抵消长度差。
                    first = first.next if first else headB
                    second = second.next if second else headA
                return first
        ''', '''
        class Solution {
        public:
            ListNode* getIntersectionNode(ListNode* headA, ListNode* headB) {
                ListNode* first = headA;
                ListNode* second = headB;
                while (first != second) {
                    // 两个指针都走过 A+B 的总长度。
                    first = first ? first->next : headB;
                    second = second ? second->next : headA;
                }
                return first;
            }
        };
        ''', '两个指针分别遍历 A 再 B、B 再 A，利用相同总路程抵消长度差。',
        ['两个指针分别从两个头节点出发。','每次各走一步，到 null 后切换到另一个头节点。','指针对象相同时返回，可能是交点，也可能是 null。'],
        '设独有前缀长为 a、b，共享后缀长为 c。换链后两个指针到交点都经过 a+b+c 个节点，必然在交点相遇；若没有相交，则各走完两条链后同时为 null。',
        ['比较节点身份，不能比较 val。','到 null 后再换链，不能在尾节点提前切换。'], 'O(m+n)', 'O(1)', special='intersection'),

    problem(206, '反转链表', 'reverse-linked-list', '简单', '链表',
        '将单链表的 next 方向逐一反转，返回反转后链表的新头节点。空链表应返回 null。',
        ['0 ≤ 节点数 ≤ 5000', '链表无环'],
        [([[1,2,3,4,5]],[5,4,3,2,1],'尾节点成为新的头节点。'), ([[]],[],'空链表仍为空。')],
        'reverseList', [('head','ListNode')], 'ListNode',
        '''
        from typing import Optional

        class Solution:
            def reverseList(self, head: Optional['ListNode']) -> Optional['ListNode']:
                previous = None
                current = head
                while current:
                    following = current.next  # 先保留未处理部分入口。
                    current.next = previous
                    previous = current
                    current = following
                return previous
        ''', '''
        class Solution {
        public:
            ListNode* reverseList(ListNode* head) {
                ListNode* previous = nullptr;
                ListNode* current = head;
                while (current) {
                    ListNode* following = current->next; // 改指针前保存后继。
                    current->next = previous;
                    previous = current;
                    current = following;
                }
                return previous;
            }
        };
        ''', '用 previous、current、following 三个指针依次反转每条 next 边。',
        ['previous 初始为空，current 指向头节点。','保存 current.next，再让 current.next 指向 previous。','previous 和 current 同时前进，最终返回 previous。'],
        '循环开始时 previous 是已反转前缀的头，current 是未处理后缀的头。一次操作把 current 移到反转前缀最前端，保持不变式；未处理部分为空时整个链表已反转。',
        ['修改 next 前必须保存原后继。','最终返回 previous，而不是已经为空的 current。'], 'O(n)', 'O(1)'),

    problem(234, '回文链表', 'palindrome-linked-list', '简单', '链表',
        '判断单链表从头到尾的节点值是否构成回文序列。要求线性时间和常数额外空间，解法在判断后恢复链表结构。',
        ['1 ≤ 节点数 ≤ 10⁵', '0 ≤ 节点值 ≤ 9'],
        [([[1,2,2,1]],True,'从两端向中间对应值相同。'), ([[1,2]],False,'首尾不相同。'), ([[1]],True,'单节点自然是回文。')],
        'isPalindrome', [('head','ListNode')], 'bool',
        '''
        from typing import Optional

        class Solution:
            def isPalindrome(self, head: Optional['ListNode']) -> bool:
                def reverse(node):
                    previous = None
                    while node:
                        following = node.next
                        node.next = previous
                        previous, node = node, following
                    return previous

                if not head or not head.next:
                    return True
                slow = fast = head
                while fast.next and fast.next.next:
                    slow = slow.next
                    fast = fast.next.next
                second_head = reverse(slow.next)
                left, right = head, second_head
                matches = True
                while right:
                    if left.val != right.val:
                        matches = False
                    left, right = left.next, right.next
                # 即使发现不相等，也在返回前恢复后半段。
                slow.next = reverse(second_head)
                return matches
        ''', '''
        class Solution {
            ListNode* reverse(ListNode* node) {
                ListNode* previous = nullptr;
                while (node) {
                    ListNode* following = node->next;
                    node->next = previous;
                    previous = node;
                    node = following;
                }
                return previous;
            }
        public:
            bool isPalindrome(ListNode* head) {
                if (!head || !head->next) return true;
                ListNode* slow = head;
                ListNode* fast = head;
                while (fast->next && fast->next->next) {
                    slow = slow->next;
                    fast = fast->next->next;
                }
                ListNode* secondHead = reverse(slow->next);
                ListNode* left = head;
                ListNode* right = secondHead;
                bool matches = true;
                while (right) {
                    if (left->val != right->val) matches = false;
                    left = left->next;
                    right = right->next;
                }
                slow->next = reverse(secondHead); // 恢复输入结构。
                return matches;
            }
        };
        ''', '快慢指针定位前半段尾，反转后半段后逐一比较，最后恢复后半段。',
        ['快指针一次两步，慢指针一次一步，找到前半段末尾。','反转 slow.next 开始的后半段。','从原头和后半段新头同步比较。','恢复后半段并返回比较结果。'],
        '反转后的后半段按从尾到中的顺序排列，与前半段从头到中的顺序一一对应。偶数长度比较所有节点对，奇数长度自动忽略无需比较的中间节点。因此所有比较相等当且仅当原链表回文。',
        ['比较范围以较短的后半段为准。','若要恢复链表，发现不相等时不能直接提前返回。'], 'O(n)', 'O(1)'),

    problem(141, '环形链表', 'linked-list-cycle', '简单', '链表',
        '判断链表中是否存在沿 next 能再次回到某节点的环。练习输入为 [节点值数组,pos]，pos 为尾节点连接到的下标，-1 表示尾节点指向 null；pos 仅用于构造输入，不是函数参数。',
        ['0 ≤ 节点数 ≤ 10⁴', 'pos 为 -1 或有效节点下标'],
        [([[3,2,0,-4],1],True,'尾节点连回下标 1，形成环。'), ([[1],-1],False,'唯一节点的 next 为空。'), ([[1],0],True,'单个节点也可以形成自环。')],
        'hasCycle', [('head','ListNode')], 'bool',
        '''
        from typing import Optional

        class Solution:
            def hasCycle(self, head: Optional['ListNode']) -> bool:
                slow = fast = head
                while fast and fast.next:
                    slow = slow.next
                    fast = fast.next.next
                    # 必须先移动再比较，初始同在头节点不代表有环。
                    if slow is fast:
                        return True
                return False
        ''', '''
        class Solution {
        public:
            bool hasCycle(ListNode* head) {
                ListNode* slow = head;
                ListNode* fast = head;
                while (fast && fast->next) {
                    slow = slow->next;
                    fast = fast->next->next;
                    if (slow == fast) return true; // 在环中快指针必会追上慢指针。
                }
                return false;
            }
        };
        ''', 'Floyd 快慢指针：慢指针每次一步，快指针每次两步。',
        ['两个指针同时从头节点出发。','先检查快指针能否走两步，再移动两个指针。','若移动后相遇则有环，快指针到达空节点则无环。'],
        '无环时快指针必然到达 null。有环时两个指针最终都进入环，每轮快指针相对慢指针前进一步，模环长的距离终将变为零，因此必然相遇。',
        ['需要同时检查 fast 和 fast.next。','比较节点地址，不能比较节点值。'], 'O(n)', 'O(1)', special='cycle'),

    problem(142, '环形链表 II', 'linked-list-cycle-ii', '中等', '链表',
        '若链表存在环，返回环入口节点；否则返回 null。不得修改链表。练习输入为 [节点值数组,pos]，pos 只用于构造尾节点连接位置，-1 表示无环；练习输出为入口下标，无环输出 -1。',
        ['0 ≤ 节点数 ≤ 10⁴', 'pos 为 -1 或有效节点下标'],
        [([[3,2,0,-4],1],1,'第一次进入环的位置是下标 1。'), ([[],-1],-1,'空链表没有入口。'), ([[1],0],0,'自环的入口就是头节点。')],
        'detectCycle', [('head','ListNode')], 'ListNode',
        '''
        from typing import Optional

        class Solution:
            def detectCycle(self, head: Optional['ListNode']) -> Optional['ListNode']:
                slow = fast = head
                while fast and fast.next:
                    slow = slow.next
                    fast = fast.next.next
                    if slow is fast:
                        seeker = head
                        # 一个从头开始，一个从相遇点开始，同速走到入口。
                        while seeker is not slow:
                            seeker = seeker.next
                            slow = slow.next
                        return seeker
                return None
        ''', '''
        class Solution {
        public:
            ListNode* detectCycle(ListNode* head) {
                ListNode* slow = head;
                ListNode* fast = head;
                while (fast && fast->next) {
                    slow = slow->next;
                    fast = fast->next->next;
                    if (slow == fast) {
                        ListNode* seeker = head;
                        while (seeker != slow) {
                            seeker = seeker->next;
                            slow = slow->next;
                        }
                        return seeker;
                    }
                }
                return nullptr;
            }
        };
        ''', '先让快慢指针在环内相遇，再从头节点和相遇点各出发一个同速指针寻找入口。',
        ['使用快慢指针判断是否存在相遇点。','无相遇点则返回 null。','一个指针回到头节点，另一个留在相遇点。','两者每次各走一步，再次相遇的位置即入口。'],
        '设头到入口距离为 a、入口到相遇点沿环距离为 b、环长为 L。相遇时快指针比慢指针多走若干圈，由速度比得 a+b 是 L 的倍数。因此从相遇点再走 a 步恰到入口，从头走 a 步也到入口。',
        ['第一阶段先移动后判断。','第二阶段两个指针都只走一步。','pos 不是 LeetCode 方法参数。'], 'O(n)', 'O(1)', special='cycle'),

    problem(21, '合并两个有序链表', 'merge-two-sorted-lists', '简单', '链表',
        '给定两条按非降序排列的链表，将其节点合并为一条非降序链表，返回新头节点。允许直接重新连接原节点。',
        ['每条链表包含 0 到 50 个节点', '两条链表均按非降序排列'],
        [([[1,2,4],[1,3,4]],[1,1,2,3,4,4],'相等值保留全部节点。'), ([[],[0]],[0],'一条为空时直接返回另一条。')],
        'mergeTwoLists', [('list1','ListNode'),('list2','ListNode')], 'ListNode',
        '''
        from typing import Optional

        class Solution:
            def mergeTwoLists(self, list1: Optional['ListNode'], list2: Optional['ListNode']) -> Optional['ListNode']:
                dummy = ListNode(0)
                tail = dummy
                while list1 and list2:
                    if list1.val <= list2.val:
                        tail.next = list1
                        list1 = list1.next
                    else:
                        tail.next = list2
                        list2 = list2.next
                    tail = tail.next
                # 剩余部分自身有序，可直接接到结果末尾。
                tail.next = list1 if list1 else list2
                return dummy.next
        ''', '''
        class Solution {
        public:
            ListNode* mergeTwoLists(ListNode* list1, ListNode* list2) {
                ListNode dummy(0);
                ListNode* tail = &dummy;
                while (list1 && list2) {
                    if (list1->val <= list2->val) {
                        tail->next = list1;
                        list1 = list1->next;
                    } else {
                        tail->next = list2;
                        list2 = list2->next;
                    }
                    tail = tail->next;
                }
                tail->next = list1 ? list1 : list2;
                return dummy.next;
            }
        };
        ''', '每次从两个未合并部分的头部选更小节点接到结果尾部。',
        ['建立虚拟头节点以统一首次连接。','比较两个当前头节点，连接较小者并推进该链表。','一条耗尽后接上另一条剩余部分。'],
        '每条剩余链表的头部是其最小值，二者较小者因此是全部未处理节点中的最小值。逐次选择该节点便保持结果有序，最终每个节点都恰好加入一次。',
        ['连接节点后记得推进结果 tail。','相同值要保留两份节点。'], 'O(m+n)', 'O(1)'),

    problem(2, '两数相加', 'add-two-numbers', '中等', '链表',
        '两条非空链表分别表示非负整数，各位按低位在前的顺序存储，每个节点为一位数字。返回它们和的链表，同样低位在前。除整数 0 外，输入最高位不为 0。',
        ['每条链表包含 1 到 100 个节点', '节点值为 0 到 9'],
        [([[2,4,3],[5,6,4]],[7,0,8],'342 + 465 = 807。'), ([[9,9],[1]],[0,0,1],'99 + 1 = 100，末尾仍需新增进位节点。')],
        'addTwoNumbers', [('l1','ListNode'),('l2','ListNode')], 'ListNode',
        '''
        from typing import Optional

        class Solution:
            def addTwoNumbers(self, l1: Optional['ListNode'], l2: Optional['ListNode']) -> Optional['ListNode']:
                dummy = ListNode(0)
                tail = dummy
                carry = 0
                while l1 or l2 or carry:
                    total = carry
                    if l1:
                        total += l1.val
                        l1 = l1.next
                    if l2:
                        total += l2.val
                        l2 = l2.next
                    # 当前位取余，进位留给下一位。
                    carry, digit = divmod(total, 10)
                    tail.next = ListNode(digit)
                    tail = tail.next
                return dummy.next
        ''', '''
        class Solution {
        public:
            ListNode* addTwoNumbers(ListNode* l1, ListNode* l2) {
                ListNode dummy(0);
                ListNode* tail = &dummy;
                int carry = 0;
                while (l1 || l2 || carry) {
                    int total = carry;
                    if (l1) { total += l1->val; l1 = l1->next; }
                    if (l2) { total += l2->val; l2 = l2->next; }
                    tail->next = new ListNode(total % 10);
                    tail = tail->next;
                    carry = total / 10; // 两条链表结束后仍要处理进位。
                }
                return dummy.next;
            }
        };
        ''', '按个位到高位模拟竖式加法，只维护一个进位变量。',
        ['循环读取两条链表的当前数字，不存在的位按 0 处理。','将两位与进位相加。','个位创建新节点，十位保留为下次进位。','直到两个输入和进位都耗尽。'],
        '每一轮处理的恰为相同十进制位。total % 10 给出该位正确数字，total // 10 给出传递到下一位的进位，逐位模拟十进制加法即可得到完整结果。',
        ['两条链表长度可能不同。','循环条件必须包括 carry。','不要转换为固定宽度整数，输入可能超过其表示范围。'], 'O(max(m,n))', 'O(1) 额外空间，输出 O(max(m,n))'),

    problem(19, '删除链表的倒数第 N 个结点', 'remove-nth-node-from-end-of-list', '中等', '链表',
        '给定单链表 head 与有效整数 n，删除倒数第 n 个节点并返回新的头节点。要求一次遍历完成。',
        ['1 ≤ 节点数 ≤ 30', '1 ≤ n ≤ 节点数'],
        [([[1,2,3,4,5],2],[1,2,3,5],'倒数第二个节点的值是 4。'), ([[1],1],[],'删除唯一节点后返回空链表。')],
        'removeNthFromEnd', [('head','ListNode'),('n','int')], 'ListNode',
        '''
        from typing import Optional

        class Solution:
            def removeNthFromEnd(self, head: Optional['ListNode'], n: int) -> Optional['ListNode']:
                dummy = ListNode(0, head)
                fast = slow = dummy
                for _ in range(n):
                    fast = fast.next
                while fast.next:
                    fast = fast.next
                    slow = slow.next
                # fast 到达尾部时，slow 恰好在待删除节点之前。
                slow.next = slow.next.next
                return dummy.next
        ''', '''
        class Solution {
        public:
            ListNode* removeNthFromEnd(ListNode* head, int n) {
                ListNode dummy(0, head);
                ListNode* fast = &dummy;
                ListNode* slow = &dummy;
                for (int step = 0; step < n; ++step) fast = fast->next;
                while (fast->next) {
                    fast = fast->next;
                    slow = slow->next;
                }
                slow->next = slow->next->next; // 虚拟头统一处理删除头节点。
                return dummy.next;
            }
        };
        ''', '快指针先领先 n 个节点，然后同步前进，让慢指针停在待删除节点的前驱。',
        ['虚拟头节点指向原头，两个指针从虚拟头出发。','快指针先走 n 步。','快指针未到尾时两个指针同步走。','让慢指针绕过其后继节点。'],
        '两个指针始终相隔 n 步。当快指针停在第 L 个节点时，慢指针位于第 L-n 个节点；待删除倒数第 n 个节点编号为 L-n+1，因此慢指针正是其前驱。',
        ['本写法先走 n 步，停止条件是 fast.next 为空。','删除头节点时必须返回 dummy.next。'], 'O(L)，L 为节点数', 'O(1)'),

    problem(24, '两两交换链表中的节点', 'swap-nodes-in-pairs', '中等', '链表',
        '将链表相邻节点两两交换，返回新的头节点。必须交换节点连接关系，不能只修改节点值；奇数长度时最后一个节点保持原位。',
        ['0 ≤ 节点数 ≤ 100', '链表无环'],
        [([[1,2,3,4]],[2,1,4,3],'第一对与第二对分别交换。'), ([[1,2,3]],[2,1,3],'最后一个节点没有配对，保持原位。'), ([[]],[],'空链表无需处理。')],
        'swapPairs', [('head','ListNode')], 'ListNode',
        '''
        from typing import Optional

        class Solution:
            def swapPairs(self, head: Optional['ListNode']) -> Optional['ListNode']:
                dummy = ListNode(0, head)
                previous = dummy
                while previous.next and previous.next.next:
                    first = previous.next
                    second = first.next
                    # previous -> first -> second 变成 previous -> second -> first。
                    first.next = second.next
                    second.next = first
                    previous.next = second
                    previous = first
                return dummy.next
        ''', '''
        class Solution {
        public:
            ListNode* swapPairs(ListNode* head) {
                ListNode dummy(0, head);
                ListNode* previous = &dummy;
                while (previous->next && previous->next->next) {
                    ListNode* first = previous->next;
                    ListNode* second = first->next;
                    first->next = second->next;
                    second->next = first;
                    previous->next = second;
                    previous = first; // 原 first 成为这一对的末尾。
                }
                return dummy.next;
            }
        };
        ''', '虚拟头加前驱指针，每次重新连接一对节点，然后让前驱移动到这一对的新尾部。',
        ['确认后面至少有两个节点。','保存 first 和 second。','将前驱连到 second，second 连到 first，first 连到下一段。','前驱移动到 first，继续处理下一对。'],
        '每轮只改变当前两节点与前后边界的连接，值和其余顺序均不变。前驱始终位于已处理前缀尾部，因此各对互不干扰，剩余不足两节点时保持原样。',
        ['交换完成后 previous 指向 first，而不是 second。','必须检查两个后继都存在。'], 'O(n)', 'O(1)'),

    problem(25, 'K 个一组翻转链表', 'reverse-nodes-in-k-group', '困难', '链表',
        '将链表从头开始按每 k 个节点分组，在每组内部反转节点连接。末尾不足 k 个节点的一组保持原顺序，不能仅交换节点值。',
        ['1 ≤ k ≤ 节点数 ≤ 5000', '链表无环'],
        [([[1,2,3,4,5],2],[2,1,4,3,5],'前两组各两个节点反转，最后一个不动。'), ([[1,2,3,4,5],3],[3,2,1,4,5],'末尾两个节点不足一组，保持原位。')],
        'reverseKGroup', [('head','ListNode'),('k','int')], 'ListNode',
        '''
        from typing import Optional

        class Solution:
            def reverseKGroup(self, head: Optional['ListNode'], k: int) -> Optional['ListNode']:
                dummy = ListNode(0, head)
                group_previous = dummy
                while True:
                    kth = group_previous
                    for _ in range(k):
                        kth = kth.next
                        if kth is None:
                            return dummy.next
                    group_next = kth.next
                    previous, current = group_next, group_previous.next
                    # 以组后继为终点反转，自动连接下一组。
                    while current is not group_next:
                        following = current.next
                        current.next = previous
                        previous, current = current, following
                    old_head = group_previous.next
                    group_previous.next = kth
                    group_previous = old_head
        ''', '''
        class Solution {
        public:
            ListNode* reverseKGroup(ListNode* head, int k) {
                ListNode dummy(0, head);
                ListNode* groupPrevious = &dummy;
                while (true) {
                    ListNode* kth = groupPrevious;
                    for (int step = 0; step < k; ++step) {
                        kth = kth->next;
                        if (!kth) return dummy.next;
                    }
                    ListNode* groupNext = kth->next;
                    ListNode* previous = groupNext;
                    ListNode* current = groupPrevious->next;
                    while (current != groupNext) {
                        ListNode* following = current->next;
                        current->next = previous;
                        previous = current;
                        current = following;
                    }
                    ListNode* oldHead = groupPrevious->next;
                    groupPrevious->next = kth;
                    groupPrevious = oldHead; // 原组头成为新组尾。
                }
            }
        };
        ''', '先确认完整一组存在，再原地反转这一组，并把组头、组尾接回整体链表。',
        ['从组前驱向后寻找第 k 个节点，不足则直接结束。','保存组后继，并用它作为反转时 previous 的初值。','反转当前组所有节点。','前一组连接新组头，当前组原头作为下一轮的前驱。'],
        '只有确认存在 k 个节点才进行反转，保证不足组保持原状。组内反转把每条连接方向倒转，初始 previous 为组后继使原组头最终仍连向未处理部分，再连接新组头即可保持整链表完整。',
        ['确认节点数量之前不要开始反转。','保存 group_next，不能依赖反转后的 kth.next。'], 'O(n)', 'O(1)'),

    problem(138, '随机链表的复制', 'copy-list-with-random-pointer', '中等', '链表',
        '每个节点含 val、next、random，random 可以指向链表中任意节点或 null。请深拷贝整条链表，使副本不引用原节点，并保持相同的 next 与 random 关系。练习用 [值,random目标下标或null] 的数组表示链表。',
        ['0 ≤ 节点数 ≤ 1000', 'random 为 null 或指向本链表某节点'],
        [([[[7,None],[13,0],[11,4],[10,2],[1,0]]],[[7,None],[13,0],[11,4],[10,2],[1,0]],'副本的值和随机指向下标相同，但所有节点都是新对象。'), ([[]],[],'空链表的深拷贝仍为空。'), ([[[1,0]]],[[1,0]],'副本 random 指向副本自身。')],
        'copyRandomList', [('head','Node')], 'Node',
        '''
        from typing import Optional

        class Solution:
            def copyRandomList(self, head: Optional['Node']) -> Optional['Node']:
                if head is None:
                    return None
                current = head
                while current:
                    copied = Node(current.val)
                    copied.next = current.next
                    current.next = copied
                    current = copied.next
                current = head
                while current:
                    # 每个原节点后面紧跟其副本，省去映射表。
                    current.next.random = current.random.next if current.random else None
                    current = current.next.next
                copied_head = head.next
                current = head
                while current:
                    copied = current.next
                    current.next = copied.next
                    copied.next = current.next.next if current.next else None
                    current = current.next
                return copied_head
        ''', '''
        class Solution {
        public:
            Node* copyRandomList(Node* head) {
                if (!head) return nullptr;
                for (Node* current = head; current; current = current->next->next) {
                    Node* copied = new Node(current->val);
                    copied->next = current->next;
                    current->next = copied;
                }
                for (Node* current = head; current; current = current->next->next)
                    current->next->random = current->random ? current->random->next : nullptr;
                Node* copiedHead = head->next;
                for (Node* current = head; current;) {
                    Node* copied = current->next;
                    current->next = copied->next; // 还原原链表的 next。
                    copied->next = current->next ? current->next->next : nullptr;
                    current = current->next;
                }
                return copiedHead;
            }
        };
        ''', '把每个副本临时插在原节点后面，用相邻关系找到 random 目标的副本，最后拆分两条链表。',
        ['把 A→B 改成 A→A副本→B→B副本。','令每个副本的 random 指向原 random 目标的 next。','拆出副本链表，同时恢复原链表。'],
        '交织后原节点 x 的副本始终是 x.next。原节点 random 指向 y 时，副本正确目标就是 y.next。全部 random 赋好后，拆分仅改变 next，不改变已建立的随机关系，最终两条链表相互独立。',
        ['全部副本插入后，才能开始设置 random。','拆分时必须同时恢复原链表。','额外空间不计创建的输出节点。'], 'O(n)', 'O(1) 额外空间，输出 O(n)', special='random-list'),

    problem(148, '排序链表', 'sort-list', '中等', '链表',
        '将单链表按节点值从小到大排序并返回新的头节点。要求 O(n log n) 时间和常数额外空间。',
        ['0 ≤ 节点数 ≤ 5 × 10⁴', '-10⁵ ≤ 节点值 ≤ 10⁵'],
        [([[4,2,1,3]],[1,2,3,4],'按值升序重新连接节点。'), ([[]],[],'空链表直接返回。'), ([[2,1,2]],[1,2,2],'重复值全部保留。')],
        'sortList', [('head','ListNode')], 'ListNode',
        '''
        from typing import Optional

        class Solution:
            def sortList(self, head: Optional['ListNode']) -> Optional['ListNode']:
                def cut(node, width):
                    if node is None:
                        return None
                    for _ in range(width - 1):
                        if node.next is None:
                            break
                        node = node.next
                    remainder = node.next
                    node.next = None
                    return remainder

                def merge(left, right, tail):
                    while left and right:
                        if left.val <= right.val:
                            tail.next, left = left, left.next
                        else:
                            tail.next, right = right, right.next
                        tail = tail.next
                    tail.next = left if left else right
                    while tail.next:
                        tail = tail.next
                    return tail

                length = 0
                current = head
                while current:
                    length += 1
                    current = current.next
                dummy = ListNode(0, head)
                width = 1
                while width < length:
                    tail, current = dummy, dummy.next
                    while current:
                        left = current
                        right = cut(left, width)
                        current = cut(right, width)
                        tail = merge(left, right, tail)
                    # 有序段长度逐轮翻倍，不使用递归栈。
                    width *= 2
                return dummy.next
        ''', '''
        class Solution {
            ListNode* cut(ListNode* node, int width) {
                if (!node) return nullptr;
                for (int i = 1; i < width && node->next; ++i) node = node->next;
                ListNode* remainder = node->next;
                node->next = nullptr;
                return remainder;
            }
            ListNode* merge(ListNode* left, ListNode* right, ListNode* tail) {
                while (left && right) {
                    if (left->val <= right->val) { tail->next = left; left = left->next; }
                    else { tail->next = right; right = right->next; }
                    tail = tail->next;
                }
                tail->next = left ? left : right;
                while (tail->next) tail = tail->next;
                return tail;
            }
        public:
            ListNode* sortList(ListNode* head) {
                int length = 0;
                for (ListNode* node = head; node; node = node->next) ++length;
                ListNode dummy(0, head);
                for (int width = 1; width < length; width *= 2) {
                    ListNode* tail = &dummy;
                    ListNode* current = dummy.next;
                    while (current) {
                        ListNode* left = current;
                        ListNode* right = cut(left, width);
                        current = cut(right, width);
                        tail = merge(left, right, tail);
                    }
                }
                return dummy.next;
            }
        };
        ''', '自底向上的归并排序，依次合并长度为 1、2、4、8……的相邻有序链段。',
        ['遍历一次获得链表长度。','将链表按当前 width 截成一对对相邻链段。','用双指针合并每对有序链段，并接回输出尾部。','width 翻倍，直到整条链表成为一个有序段。'],
        '初始单节点段天然有序。若某轮所有长度不超过 width 的段有序，合并相邻两段会得到长度不超过 2×width 的有序段。逐轮归纳，段长覆盖整链表后即全局有序；所有节点通过重新连接保留。',
        ['cut 必须断开 next，避免合并时跨入下一段。','末尾不足 width 的链段也要正常处理。','采用迭代归并才能省去 O(log n) 递归栈。'], 'O(n log n)', 'O(1)'),

    problem(23, '合并 K 个升序链表', 'merge-k-sorted-lists', '困难', '堆',
        '给定 k 条非降序链表，将全部节点合并成一条非降序链表并返回头节点。输入列表或其中的链表都可能为空。',
        ['0 ≤ k ≤ 10⁴', '所有链表节点总数 N ≤ 10⁴', '每条链表均按非降序排列'],
        [([[[1,4,5],[1,3,4],[2,6]]],[1,1,2,3,4,4,5,6],'每次从各链表当前头节点中取最小者。'), ([[]],[],'没有输入链表。'), ([[[],[]]],[],'所有输入链表均为空。')],
        'mergeKLists', [('lists','ListNode[]')], 'ListNode',
        '''
        from typing import List, Optional
        import heapq

        class Solution:
            def mergeKLists(self, lists: List[Optional['ListNode']]) -> Optional['ListNode']:
                heap = [(node.val, index, node) for index, node in enumerate(lists) if node]
                heapq.heapify(heap)
                dummy = ListNode(0)
                tail = dummy
                while heap:
                    _, index, node = heapq.heappop(heap)
                    tail.next = node
                    tail = node
                    if node.next:
                        # 同值时比较链表编号，避免直接比较节点对象。
                        heapq.heappush(heap, (node.next.val, index, node.next))
                return dummy.next
        ''', '''
        class Solution {
            struct Greater {
                bool operator()(ListNode* left, ListNode* right) const {
                    return left->val > right->val;
                }
            };
        public:
            ListNode* mergeKLists(vector<ListNode*>& lists) {
                priority_queue<ListNode*, vector<ListNode*>, Greater> heap;
                for (ListNode* node : lists) if (node) heap.push(node);
                ListNode dummy(0);
                ListNode* tail = &dummy;
                while (!heap.empty()) {
                    ListNode* node = heap.top();
                    heap.pop();
                    tail->next = node;
                    tail = node;
                    // 每条链表在堆中最多保留一个当前候选。
                    if (node->next) heap.push(node->next);
                }
                return dummy.next;
            }
        };
        ''', '最小堆维护每条非空链表当前最小的候选节点，每次取堆顶并补入该节点的后继。',
        ['将所有非空链表的头节点加入最小堆。','弹出最小节点，连接到结果尾部。','若它有后继，将后继加入堆。','堆空后返回结果链表。'],
        '每条未耗尽链表的最小剩余节点都在堆中，因此堆顶是全局最小剩余节点。取出后用同链表后继补位，不变式持续成立，输出遂为全部节点的非降序排列。',
        ['Python 元组必须加入编号，避免相同值时比较 ListNode。','空链表不入堆。','C++ priority_queue 默认最大堆，需要自定义比较器。'], 'O(k + N log(k+1))', 'O(k)'),
])
