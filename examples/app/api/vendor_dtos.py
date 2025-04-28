# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
DTOs for Vendor API (Uno example app).
Defines the canonical data transfer object for Vendor aggregate API responses.
"""
from pydantic import EmailStr
from uno.core.application.dtos.dto import DTO

class VendorDTO(DTO):
    """
    Canonical DTO for Vendor API serialization.

    Attributes:
        id: Unique vendor ID.
        name: Vendor name.
        contact_email: Vendor contact email (validated, RFC-compliant).
    """
    id: str
    name: str
    contact_email: EmailStr
