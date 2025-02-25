import json
import re
from pathlib import Path
from datetime import datetime
from pkg.plugin.context import register, handler, BasePlugin, APIHost, EventContext
from pkg.plugin.events import (
    GroupNormalMessageReceived,
    PersonNormalMessageReceived,
    NormalMessageResponded
)

@register(
    name="GroupMemoryPro",
    description="基于多维情感模型的伪记忆系统",
    version="0.2",  # 更新版本号
    author="KL"
)
class RelationManager(BasePlugin):
    def __init__(self, host: APIHost):
        super().__init__(host)
        self.data_path = Path("plugins/GroupMemoryPro/data/relation_data.json")
        self.relation_data = {}
        # 更新正则表达式以匹配各个维度的评分调整
        self.pattern = re.compile(
            r"(评价值\s*([+-]?\d+)|评价值\s*[：:]\s*([+-]?\d+)|评分\s*([+-]?\d+)|)"
            r"(信任度|好感度|互惠性|亲密度|情绪支持)[：:]\s*([+-]?\d+)"
        )
        
        # 默认管理员列表
        self.admin_users = ["3224478440"]  # 替换为实际的管理员用户ID

        # 多维情感模型权重
        self.dimension_weights = {
            "trust": 0.3,       # 信任度
            "favor": 0.25,      # 好感度
            "reciprocity": 0.2, # 互惠性
            "intimacy": 0.15,   # 亲密度
            "emotional_support": 0.1  # 情绪支持
        }

    async def initialize(self):
        """插件初始化时加载数据"""
        await self.load_data()

    async def load_data(self):
        """加载用户关系数据"""
        try:
            if self.data_path.exists():
                with open(self.data_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:
                        self.relation_data = {}
                    else:
                        self.relation_data = json.loads(content)
        except json.JSONDecodeError as e:
            self.ap.logger.error(f"JSON 解析失败: {str(e)}")
            self.relation_data = {}
        except Exception as e:
            self.ap.logger.error(f"加载数据失败: {str(e)}")
            self.relation_data = {}

    async def save_data(self):
        """保存用户关系数据"""
        try:
            temp_path = self.data_path.with_suffix(".tmp")
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self.relation_data, f, ensure_ascii=False, indent=2)
            temp_path.replace(self.data_path)
        except Exception as e:
            self.ap.logger.error(f"保存数据失败: {str(e)}")

    def get_relation(self, user_id: str) -> dict:
        """获取或初始化用户关系数据"""
        return self.relation_data.setdefault(user_id, {
            "evaluation": 30,  # 综合评分
            "trust": 25,       # 信任度
            "favor": 25,       # 好感度
            "reciprocity": 0,  # 互惠性
            "intimacy": 25,    # 亲密度
            "emotional_support": 25,  # 情绪支持
            "history": [],
            "last_interaction": datetime.now().isoformat(),
            "custom_note": "",
            "interaction_count": 0
        })

    def calculate_evaluation(self, user_data: dict) -> float:
        """计算综合评分"""
        return sum(
            user_data[dimension] * weight
            for dimension, weight in self.dimension_weights.items()
        )

    def is_admin(self, user_id: str) -> bool:
        """检查用户是否为管理员"""
        return user_id in self.admin_users

    @handler(PersonNormalMessageReceived)
    @handler(GroupNormalMessageReceived)
    async def handle_message(self, ctx: EventContext):
        """处理用户消息"""
        user_id = str(ctx.event.sender_id)
        relation = self.get_relation(user_id)
        
        # 更新互动数据
        relation["interaction_count"] += 1
        relation["last_interaction"] = datetime.now().isoformat()
        await self.save_data()

        # 处理管理员指令
        if self.is_admin(user_id):
            if ctx.event.text_message.startswith("/修改用户"):
                await self.handle_modify_evaluation(ctx)
                return
            elif ctx.event.text_message.startswith("/增加标签"):
                await self.handle_add_tag(ctx)
                return
            elif ctx.event.text_message.startswith("/删除标签"):
                await self.handle_remove_tag(ctx)
                return
            elif ctx.event.text_message.startswith("/调整维度"):
                await self.handle_adjust_dimension(ctx)
                return

        # 普通用户指令
        if ctx.event.text_message.strip() == "/查看关系":
            report = (
                f"【关系状态】\n"
                f"• 综合评分：{self.calculate_evaluation(relation):.1f}/100\n"
                f"• 信任度：{relation['trust']:.1f}\n"
                f"• 好感度：{relation['favor']:.1f}\n"
                f"• 互惠性：{relation['reciprocity']:.1f}\n"
                f"• 亲密度：{relation['intimacy']:.1f}\n"
                f"• 情绪支持：{relation['emotional_support']:.1f}\n"
                f"• 互动次数：{relation['interaction_count']}次\n"
                f"• 最后互动：{relation['last_interaction'][:19]}\n"
                f"• 特别备注：{relation['custom_note'] or '暂无'}"
            )
            ctx.event.reply = [report]
            ctx.prevent_default()

        # 动态修改默认提示
        if hasattr(ctx.event, 'alter'):
            relation_prompt = (
                f"[当前用户关系档案]\n"
                f"用户ID: {user_id}\n"
                f"综合评分: {self.calculate_evaluation(relation):.1f}/100\n"
                f"信任度: {relation['trust']:.1f}\n"
                f"好感度: {relation['favor']:.1f}\n"
                f"互惠性: {relation['reciprocity']:.1f}\n"
                f"亲密度: {relation['intimacy']:.1f}\n"
                f"情绪支持: {relation['emotional_support']:.1f}\n"
                f"历史互动: {relation['interaction_count']}次\n"
                f"最后活跃: {relation['last_interaction'][:19]}"
                f"特别备注: {relation['custom_note'] or '暂无'}"
            )
            ctx.event.alter = f"{relation_prompt}\n\n{ctx.event.alter or ctx.event.text_message}"

    async def handle_modify_evaluation(self, ctx: EventContext):
        """处理修改评价分指令"""
        try:
            parts = ctx.event.text_message.split()
            target_user = parts[1]
            new_evaluation = int(parts[3])
            
            if not target_user or new_evaluation is None:
                raise ValueError("参数错误")
            
            relation = self.get_relation(target_user)
            old_evaluation = self.calculate_evaluation(relation)
            relation["evaluation"] = new_evaluation
            relation["history"].append({
                "timestamp": datetime.now().isoformat(),
                "adjustment": new_evaluation - old_evaluation,
                "reason": "管理员手动调整"
            })
            await self.save_data()
            
            ctx.event.reply = [f"用户 {target_user} 的综合评分已从 {old_evaluation:.1f} 修改为 {new_evaluation}。"]
            ctx.prevent_default()
        except Exception as e:
            ctx.event.reply = [f"修改评价分失败: {str(e)}"]
            ctx.prevent_default()

    async def handle_add_tag(self, ctx: EventContext):
        """处理增加标签指令"""
        try:
            parts = ctx.event.text_message.split()
            target_user = parts[1]
            tag = parts[2]
            
            if not target_user or not tag:
                raise ValueError("参数错误")
            
            relation = self.get_relation(target_user)
            relation["custom_note"] = tag
            await self.save_data()
            
            ctx.event.reply = [f"已为用户 {target_user} 添加标签: {tag}。"]
            ctx.prevent_default()
        except Exception as e:
            ctx.event.reply = [f"增加标签失败: {str(e)}"]
            ctx.prevent_default()

    async def handle_remove_tag(self, ctx: EventContext):
        """处理删除标签指令"""
        try:
            parts = ctx.event.text_message.split()
            target_user = parts[1]
            
            if not target_user:
                raise ValueError("参数错误")
            
            relation = self.get_relation(target_user)
            relation["custom_note"] = ""
            await self.save_data()
            
            ctx.event.reply = [f"已移除用户 {target_user} 的标签。"]
            ctx.prevent_default()
        except Exception as e:
            ctx.event.reply = [f"删除标签失败: {str(e)}"]
            ctx.prevent_default()

    async def handle_adjust_dimension(self, ctx: EventContext):
        """处理调整维度指令"""
        try:
            parts = ctx.event.text_message.split()
            target_user = parts[1]
            dimension = parts[2]
            value = float(parts[3])
            
            if not target_user or dimension not in self.dimension_weights:
                raise ValueError("参数错误")
            
            relation = self.get_relation(target_user)
            old_value = relation.get(dimension, 0)
            relation[dimension] = max(0, min(100, old_value + value))
            relation["history"].append({
                "timestamp": datetime.now().isoformat(),
                "adjustment": value,
                "reason": f"管理员调整 {dimension}"
            })
            await self.save_data()
            
            ctx.event.reply = [f"用户 {target_user} 的 {dimension} 已从 {old_value:.1f} 调整为 {relation[dimension]:.1f}。"]
            ctx.prevent_default()
        except Exception as e:
            ctx.event.reply = [f"调整维度失败: {str(e)}"]
            ctx.prevent_default()

    @handler(NormalMessageResponded)
    async def handle_response(self, ctx: EventContext):
        """处理AI回复"""
        event = ctx.event
        user_id = str(event.sender_id)
        
        if not hasattr(event, 'response_text') or not event.response_text:
            return

        # 提取评价值调整
        matches = self.pattern.findall(event.response_text)
        total_adjustment = 0
        cleaned_response = event.response_text

        for match in matches:
            if match[0] or match[1]:  # 评价值调整
                value = match[0] or match[1]
                try:
                    adjustment = int(value)
                    total_adjustment += adjustment
                    cleaned_response = cleaned_response.replace(match[0] or match[1], "", 1)
                except ValueError:
                    self.ap.logger.warning(f"无效的评价值数值: {value}")
                    
            else:  # 各个维度的调整
                dimension = match[3]
                value = match[4]
                
                if dimension and value:
                    try:
                        adjustment = int(value)
                        total_adjustment += adjustment
                        # 更新相应维度的值
                        relation = self.get_relation(user_id)
                        old_dimension_value = relation[dimension]
                        relation[dimension] = max(0, min(100, old_dimension_value + adjustment))
                        relation["history"].append({
                            "timestamp": datetime.now().isoformat(),
                            "adjustment": adjustment,
                            "reason": f"AI自动调整 {dimension}"
                        })
                    except ValueError:
                        self.ap.logger.warning(f"无效的 {dimension} 数值: {value}")

        # 更新综合评价值
        if total_adjustment != 0:
            relation = self.get_relation(user_id)
            new_evaluation = max(0, min(100, relation["evaluation"] + total_adjustment))
            actual_adjustment = new_evaluation - relation["evaluation"]
            relation["evaluation"] = new_evaluation
            relation["history"].append({
                "timestamp": datetime.now().isoformat(),
                "adjustment": actual_adjustment,
                "reason": "AI自动调整综合评分"
            })
            relation["last_interaction"] = datetime.now().isoformat()
            await self.save_data()
            
            # 更新回复内容
            ctx.event.response_text = (
                f"{cleaned_response.strip()}\n"
                f"[系统提示] 评价值已更新，当前为 {new_evaluation}/100。"
            )

    def __del__(self):
        pass
