# Shared constants across history package
# If you find yourself copy-pasting these values, they belong here

DEFAULT_MESSAGE_THRESHOLD = 50
DEFAULT_TOKEN_LIMIT = 4000
DEFAULT_MAX_SUMMARIES = 5
DEFAULT_SLIDING_WINDOW_SIZE = 20
DEFAULT_TIME_INTERVAL_MINUTES = 30
DEFAULT_VECTOR_MAX_RESULTS = 3
DEFAULT_VECTOR_SCORE_THRESHOLD = 0.7

# Memory strategy types
MEMORY_TYPES = {
    "smart_window": "optorch.history.types.SmartWindow",
    "token_budget": "optorch.history.types.TokenBudget",
    "hierarchical": "optorch.history.types.Hierarchical"
}

# Storage strategy types
STORAGE_TYPES = {
    "raw": "optorch.history.storage.RawStorage",
    "summary": "optorch.history.storage.SummaryStorage",
    "filtered": "optorch.history.storage.FilteredStorage",
    "hybrid": "optorch.history.storage.HybridStorage"
}

# Search strategy types
SEARCH_TYPES = {
    "always": "optorch.history.search.AlwaysSearch",
    "on_demand": "optorch.history.search.OnDemandSearch",
    "threshold": "optorch.history.search.ThresholdSearch",
    "never": "optorch.history.search.NeverSearch"
}

# Filter types
FILTER_TYPES = {
    "error": "optorch.history.filters.ErrorFilter",
    "duplicate": "optorch.history.filters.DuplicateFilter",
    "length": "optorch.history.filters.LengthFilter",
    "role": "optorch.history.filters.RoleFilter",
    "noise": "optorch.history.filters.NoiseFilter",
    "tool": "optorch.history.filters.ToolFilter",
    "time": "optorch.history.filters.TimeRangeFilter",
    "composite": "optorch.history.filters.CompositeFilter"
}

