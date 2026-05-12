from typing import Any, Dict, Optional, AsyncIterator, cast
from .base_state import BaseState
from .state import State
from .streaming_state import StreamingState


class StateFactory:
    """Factory for creating appropriate state instances."""
    
    @staticmethod
    def create(data: Optional[Dict[str, Any]] = None, stream: Optional[AsyncIterator] = None) -> BaseState:
        """
        Create appropriate state type based on parameters.
        
        Args:
            data: Initial state data
            stream: Optional async iterator for streaming
            
        Returns:
            StreamingState if stream provided, otherwise State
        """
        if stream is not None:
            return StreamingState(data, stream)
        else:
            return State(data)
    
    @staticmethod
    def from_state(existing_state: BaseState, stream: Optional[AsyncIterator] = None) -> BaseState:
        """
        Convert existing state to streaming state or copy to new state.
        
        Args:
            existing_state: Existing state to convert
            stream: Optional async iterator for streaming
            
        Returns:
            New state with existing data, streaming if stream provided
        """
        if isinstance(existing_state, (State, StreamingState)) and hasattr(existing_state, '_data'):
            data = existing_state._data.copy()
        else:
            data = existing_state.to_dict()
        
        if stream is not None:
            return StreamingState(data, stream)
        else:
            return cast(State, State(data))
    
    @staticmethod
    def make_streaming(existing_state: BaseState, stream: AsyncIterator) -> StreamingState:
        """
        Convert any state to streaming state.
        
        Args:
            existing_state: State to convert
            stream: Async iterator for streaming
            
        Returns:
            StreamingState with existing data and stream
        """
        if isinstance(existing_state, StreamingState):
            return existing_state.set_stream(stream)
        
        return cast(StreamingState, StateFactory.from_state(existing_state, stream))
    
    @staticmethod
    def make_static(existing_state: BaseState) -> State:
        """
        Convert any state to static (non-streaming) state.
        
        Args:
            existing_state: State to convert
            
        Returns:
            Static State with existing data
        """
        return cast(State, StateFactory.from_state(existing_state, stream=None))