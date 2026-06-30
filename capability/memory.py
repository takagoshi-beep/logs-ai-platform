"""
Capability Memory System for AI OS.

Implements 7-layer memory architecture for capabilities:
1. TemplateMemory - Template usage tracking
2. FieldMappingMemory - Field mapping tracking
3. DocumentPatternMemory - Document recognition patterns
4. UserCorrectionMemory - User corrections and feedback
5. OutputHistoryMemory - Generated output tracking
6. ExecutionHistoryMemory - Complete execution records
7. ValidationMemory - Validation results and errors
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class MemoryScope(str, Enum):
    """Scope of memory item."""

    USER = "user"
    TEAM = "team"
    COMPANY = "company"


@dataclass
class MemoryItem:
    """Base class for memory items."""

    item_id: str
    capability_id: str
    scope: MemoryScope
    confidence: float = 0.0  # 0-1.0
    version: str = "1.0"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    source_trace_id: str = ""
    project_id: Optional[str] = None
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    team_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "capability_id": self.capability_id,
            "scope": self.scope.value,
            "confidence": self.confidence,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class TemplateMemory(MemoryItem):
    """Template usage and effectiveness tracking."""

    template_id: str = ""
    template_name: str = ""
    used_count: int = 0
    success_count: int = 0
    user_rating: float = 0.0  # 0-5.0
    last_used_at: Optional[datetime] = None
    industry: Optional[str] = None
    amount_range_min: Optional[float] = None
    amount_range_max: Optional[float] = None


@dataclass
class FieldMappingMemory(MemoryItem):
    """Field mapping accuracy and effectiveness."""

    mapping_id: str = ""
    field_name: str = ""
    target_field: str = ""
    accuracy: float = 0.0  # 0-1.0
    times_applied: int = 0
    times_correct: int = 0
    transformation_rule: Optional[str] = None


@dataclass
class DocumentPatternMemory(MemoryItem):
    """Document recognition patterns."""

    pattern_id: str = ""
    document_type: str = ""  # "invoice", "delivery_note", "proposal", etc.
    recognition_rule: str = ""
    accuracy: float = 0.0
    times_applied: int = 0
    times_correct: int = 0
    keywords: list[str] = field(default_factory=list)


@dataclass
class UserCorrectionMemory(MemoryItem):
    """User corrections and feedback."""

    correction_id: str = ""
    execution_id: str = ""
    field_name: str = ""
    original_value: str = ""
    corrected_value: str = ""
    correction_type: str = ""  # "typo", "logic", "format", "data"
    is_recurring: bool = False
    correction_frequency: int = 0


@dataclass
class OutputHistoryMemory(MemoryItem):
    """Generated output tracking and reusability."""

    output_id: str = ""
    output_filename: str = ""
    output_format: str = ""  # "xlsx", "pdf", "docx", etc.
    output_size_bytes: int = 0
    reuse_count: int = 0
    quality_score: float = 0.0  # 0-1.0
    last_reused_at: Optional[datetime] = None


@dataclass
class ExecutionHistoryMemory(MemoryItem):
    """Complete execution records."""

    execution_id: str = ""
    status: str = ""  # "completed", "failed"
    input_data: dict = field(default_factory=dict)
    output_data: dict = field(default_factory=dict)
    execution_time_seconds: float = 0.0
    error_message: Optional[str] = None


@dataclass
class ValidationMemory(MemoryItem):
    """Validation results and error patterns."""

    validation_id: str = ""
    error_type: str = ""
    error_message: str = ""
    error_frequency: int = 0
    resolution_rule: Optional[str] = None
    auto_fixable: bool = False


class CapabilityMemory:
    """
    Memory management system for capabilities.

    Implements 7-layer memory with scope support and CRUD operations.
    """

    def __init__(self):
        self._templates: dict[str, TemplateMemory] = {}
        self._field_mappings: dict[str, FieldMappingMemory] = {}
        self._document_patterns: dict[str, DocumentPatternMemory] = {}
        self._user_corrections: dict[str, UserCorrectionMemory] = {}
        self._output_history: dict[str, OutputHistoryMemory] = {}
        self._execution_history: dict[str, ExecutionHistoryMemory] = {}
        self._validation_errors: dict[str, ValidationMemory] = {}

    # Template Memory Operations
    def add_template_memory(self, memory: TemplateMemory) -> str:
        """Add a template memory record."""
        self._templates[memory.item_id] = memory
        return memory.item_id

    def get_template_memory(self, item_id: str) -> Optional[TemplateMemory]:
        """Get template memory by ID."""
        return self._templates.get(item_id)

    def list_template_memory(
        self,
        capability_id: str,
        scope: Optional[MemoryScope] = None,
    ) -> list[TemplateMemory]:
        """List template memories for capability."""
        results = [
            m for m in self._templates.values()
            if m.capability_id == capability_id
        ]
        if scope:
            results = [m for m in results if m.scope == scope]
        return sorted(results, key=lambda x: x.used_count, reverse=True)

    # Field Mapping Memory Operations
    def add_field_mapping_memory(self, memory: FieldMappingMemory) -> str:
        """Add a field mapping memory record."""
        self._field_mappings[memory.item_id] = memory
        return memory.item_id

    def get_field_mapping_memory(self, item_id: str) -> Optional[FieldMappingMemory]:
        """Get field mapping memory by ID."""
        return self._field_mappings.get(item_id)

    def list_field_mapping_memory(
        self,
        capability_id: str,
        field_name: Optional[str] = None,
    ) -> list[FieldMappingMemory]:
        """List field mapping memories."""
        results = [
            m for m in self._field_mappings.values()
            if m.capability_id == capability_id
        ]
        if field_name:
            results = [m for m in results if m.field_name == field_name]
        return sorted(results, key=lambda x: x.accuracy, reverse=True)

    # Document Pattern Memory Operations
    def add_document_pattern_memory(self, memory: DocumentPatternMemory) -> str:
        """Add a document pattern memory record."""
        self._document_patterns[memory.item_id] = memory
        return memory.item_id

    def list_document_patterns(
        self,
        capability_id: str,
        document_type: Optional[str] = None,
    ) -> list[DocumentPatternMemory]:
        """List document patterns."""
        results = [
            m for m in self._document_patterns.values()
            if m.capability_id == capability_id
        ]
        if document_type:
            results = [m for m in results if m.document_type == document_type]
        return sorted(results, key=lambda x: x.accuracy, reverse=True)

    # User Correction Memory Operations
    def add_user_correction_memory(self, memory: UserCorrectionMemory) -> str:
        """Add a user correction memory record."""
        self._user_corrections[memory.item_id] = memory
        return memory.item_id

    def list_user_corrections(
        self,
        capability_id: str,
        field_name: Optional[str] = None,
        is_recurring: Optional[bool] = None,
    ) -> list[UserCorrectionMemory]:
        """List user corrections."""
        results = [
            m for m in self._user_corrections.values()
            if m.capability_id == capability_id
        ]
        if field_name:
            results = [m for m in results if m.field_name == field_name]
        if is_recurring is not None:
            results = [m for m in results if m.is_recurring == is_recurring]
        return sorted(results, key=lambda x: x.correction_frequency, reverse=True)

    # Output History Memory Operations
    def add_output_history_memory(self, memory: OutputHistoryMemory) -> str:
        """Add output history memory record."""
        self._output_history[memory.item_id] = memory
        return memory.item_id

    def list_output_history(
        self,
        capability_id: str,
        format_type: Optional[str] = None,
    ) -> list[OutputHistoryMemory]:
        """List output history."""
        results = [
            m for m in self._output_history.values()
            if m.capability_id == capability_id
        ]
        if format_type:
            results = [m for m in results if m.output_format == format_type]
        return sorted(results, key=lambda x: x.reuse_count, reverse=True)

    # Execution History Memory Operations
    def add_execution_history_memory(self, memory: ExecutionHistoryMemory) -> str:
        """Add execution history memory record."""
        self._execution_history[memory.item_id] = memory
        return memory.item_id

    def get_execution_history(
        self,
        capability_id: str,
        limit: int = 100,
    ) -> list[ExecutionHistoryMemory]:
        """Get execution history for capability."""
        results = [
            m for m in self._execution_history.values()
            if m.capability_id == capability_id
        ]
        return sorted(results, key=lambda x: x.updated_at, reverse=True)[:limit]

    # Validation Memory Operations
    def add_validation_memory(self, memory: ValidationMemory) -> str:
        """Add validation memory record."""
        self._validation_errors[memory.item_id] = memory
        return memory.item_id

    def list_validation_errors(
        self,
        capability_id: str,
        error_type: Optional[str] = None,
    ) -> list[ValidationMemory]:
        """List validation errors."""
        results = [
            m for m in self._validation_errors.values()
            if m.capability_id == capability_id
        ]
        if error_type:
            results = [m for m in results if m.error_type == error_type]
        return sorted(results, key=lambda x: x.error_frequency, reverse=True)

    # Memory Operations
    def update_memory_item(self, item_id: str, updates: dict) -> bool:
        """Update a memory item (generic)."""
        # Try each memory type
        if item_id in self._templates:
            item = self._templates[item_id]
            for key, value in updates.items():
                if hasattr(item, key):
                    setattr(item, key, value)
            item.updated_at = datetime.utcnow()
            return True

        if item_id in self._field_mappings:
            item = self._field_mappings[item_id]
            for key, value in updates.items():
                if hasattr(item, key):
                    setattr(item, key, value)
            item.updated_at = datetime.utcnow()
            return True

        if item_id in self._user_corrections:
            item = self._user_corrections[item_id]
            for key, value in updates.items():
                if hasattr(item, key):
                    setattr(item, key, value)
            item.updated_at = datetime.utcnow()
            return True

        return False

    def delete_memory_item(self, item_id: str, scope: MemoryScope) -> bool:
        """Delete a memory item (respects scope)."""
        if item_id in self._templates:
            item = self._templates[item_id]
            if item.scope == scope:
                del self._templates[item_id]
                return True
            return False

        if item_id in self._user_corrections:
            item = self._user_corrections[item_id]
            if item.scope == scope:
                del self._user_corrections[item_id]
                return True
            return False

        return False

    def get_capability_memory_summary(self, capability_id: str) -> dict:
        """Get summary of all memory for a capability."""
        return {
            "capability_id": capability_id,
            "template_count": len([
                m for m in self._templates.values()
                if m.capability_id == capability_id
            ]),
            "field_mapping_count": len([
                m for m in self._field_mappings.values()
                if m.capability_id == capability_id
            ]),
            "document_pattern_count": len([
                m for m in self._document_patterns.values()
                if m.capability_id == capability_id
            ]),
            "user_correction_count": len([
                m for m in self._user_corrections.values()
                if m.capability_id == capability_id
            ]),
            "output_history_count": len([
                m for m in self._output_history.values()
                if m.capability_id == capability_id
            ]),
            "execution_history_count": len([
                m for m in self._execution_history.values()
                if m.capability_id == capability_id
            ]),
            "validation_error_count": len([
                m for m in self._validation_errors.values()
                if m.capability_id == capability_id
            ]),
        }
