"""
Mapping functions for Vendor aggregate <-> VendorDTO.
"""
from examples.app.domain.vendor import Vendor
from examples.app.domain.value_objects import EmailAddress
from examples.app.api.vendor_dtos import VendorDTO

def vendor_to_dto(vendor: Vendor) -> VendorDTO:
    """
    Map a Vendor aggregate to a VendorDTO for API response.
    """
    return VendorDTO(
        id=vendor.id,
        name=vendor.name,
        contact_email=vendor.contact_email.value  # EmailAddress -> str (EmailStr)
    )

def dto_to_vendor(dto: VendorDTO) -> Vendor:
    """
    Map a VendorDTO to a Vendor aggregate for domain use.
    """
    return Vendor(
        id=dto.id,
        name=dto.name,
        contact_email=EmailAddress(value=dto.contact_email)  # EmailStr -> EmailAddress
    )
