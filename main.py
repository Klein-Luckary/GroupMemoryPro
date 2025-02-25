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
    version="0.3",  # 更新版本号
    author="KL"
)
class RelationManager(BasePlugin):
    def __init__(self, host: APIHost):
        super().__init__(host)
        self.data_path = Path("plugins/GroupMemoryPro/data/relation_data.json")
        self.relation_data = {}
        
        # 正则表达式优化：匹配括号内的多维度调整指令
        self.pattern = re.compile(
            r"\(([^)]+)\)",  # 匹配括号内全部内容
            re.UNICODE
        )
        
        # 默认管理员列表
        self.admin_users = ["123456789"]  # 替换为实际的管理员用户ID

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
            "evaluation": 25,  # 综合评分，调整为较低初始值
            "trust": 25,       # 信任度，调整为较低初始值
            "favor": 25,       # 好感度，调整为较低初始值
            "reciprocity": 0,  # 互惠性，保持为0
            "intimacy": 25,    # 亲密度，调整为较低初始值
            "emotional_support": 25,  # 情绪支持，调整为较低初始值
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

    def parse_dimension_adjustments(self, text: str) -> dict:
        """解析维度调整文本"""
        adjustments = {}
        
        # 分割多个调整项
        items = re.split(r",\s*", text)
        for item in items:
            # 匹配单个维度调整
            match = re.match(
                r"^\s*(信任度|好感度|互惠性|亲密度|情绪支持)"  # 维度名
                r"[：:]?\s*"  # 可选分隔符
                r"([+-]?\d+\.?\d*)"  # 数值（支持小数和整数）
                r"\s*$", 
                item
            )
            
            if match:
                dimension = match.group(1)
                try:
                    value = float(match.group(2))
                    adjustments[dimension] = value
                except ValueError:
                    self.ap.logger.warning(f"无效数值格式: {match.group(2)}")
        
        return adjustments

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
                f"[用户关系档案]\n"
                f"用户ID: {user_id}\n"
                f"综合评分: {self.calculate_evaluation(relation):.1f}/100\n"
                f"信任度: {relation['trust']:.1f}\n"
                f"好感度: {relation['favor']:.1f}\n"
                f"互惠性: {relation['reciprocity']:.1f}\n"
                f"亲密度: {relation['intimacy']:.1f}\n"
                f"情绪支持: {relation['emotional_support']:.1f}\n"
                f"历史互动: {relation['interaction_count']}次\n"
                f"最后活跃: {relation['last_interaction'][:19]}\n"
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
            
            # 从消息中提取维度和相应的值
            match = self.pattern.search(ctx.event.text_message)
            
            if not target_user or not match:
                raise ValueError("参数错误")
            
            relation = self.get_relation(target_user)

            for dimension in ["信任度", "好感度", "互惠性", "亲密度", "情绪支持"]:
                dimension_value_match = re.search(rf"{dimension}[：:]?\s*([+-]?\d+(\.\d+)?)", match.group(0))
                
                if dimension_value_match:
                    adjustment_value = float(dimension_value_match.group(1))
                    old_value = relation[dimension]
                    relation[dimension] = max(0, min(100, old_value + adjustment_value))
                    relation["history"].append({
                        "timestamp": datetime.now().isoformat(),
                        "adjustment": adjustment_value,
                        "reason": f"管理员调整 {dimension}"
                    })
            
            await self.save_data()
            
            ctx.event.reply = [f"用户 {target_user} 的维度已更新。"]
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

        # 提取所有括号内的调整指令
        matches = self.pattern.findall(event.response_text)
        if not matches:
            return

        # 清理原始回复内容
        cleaned_response = re.sub(self.pattern, "", event.response_text).strip()
        
        # 处理每个匹配到的调整块
        relation = self.get_relation(user_id)
        for adjustment_block in matches:
            adjustments = self.parse_dimension_adjustments(adjustment_block)
            
            for dimension, value in adjustments.items():
                # 获取维度字段名映射
                dimension_map = {
                    "信任度": "trust",
                    "好感度": "favor",
                    "互惠性": "reciprocity",
                    "亲密度": "intimacy",
                    "情绪支持": "emotional_support"
                }
                
                field_name = dimension_map.get(dimension)
                if not field_name:
                    continue
                    
                # 应用调整值
                old_value = relation[field_name]
                new_value = max(0.0, min(100.0, old_value + value))
                relation[field_name] = new_value
                
                # 记录历史
                relation["history"].append({
                    "timestamp": datetime.now().isoformat(),
                    "adjustment": value,
                    "reason": f"AI自动调整 {dimension}",
                    "dimension": field_name
                })
                
                self.ap.logger.debug(
                    f"用户 {user_id} {dimension} 调整: {old_value:.1f} → {new_value:.1f}"
                )

        # 更新综合评分
        relation["evaluation"] = self.calculate_evaluation(relation)
        
        # 保存数据并更新回复
        await self.save_data()
        ctx.event.response_text = f"{cleaned_response}\n[多维评分已自动更新]"

    def __del__(self):
        pass
