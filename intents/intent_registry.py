from typing import Any
from optorch.registry import Registry
from optorch.intents.base_intent_handler import BaseIntentHandler
from optorch.intents.intent_context import IntentContext


class IntentRegistry(Registry[BaseIntentHandler]):
    async def execute(self, intent_name: str, context: IntentContext) -> dict[str, Any]:
        handler = self.get(intent_name)
        
        if not handler.should_execute(context):
            return {}
        
        return await handler.execute(context)
    
    async def execute_multiple(self, intent_names: list[str], context: IntentContext) -> dict[str, Any]:
        results = {}
        
        for intent_name in intent_names:
            if not self.has(intent_name):
                continue
            
            result = await self.execute(intent_name, context)
            results[intent_name] = result
            
            if context.skip_execution:
                break
        
        return results
