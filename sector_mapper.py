def get_sector_proposal_categories(entity_type):
    """
    Maps organizational classifications to specific proposal categories.
    """
    if "Academic" in entity_type or "University" in entity_type or "Research" in entity_type:
        return [
            "Internal Research Proposal & Grant",
            "Academic Fellowship / Doctoral Dissertation Grant",
            "Campus Infrastructure & Facilities Contract Bid",
            "Joint University-Industry R&D Collaboration",
            "Educational Technology Systems Architecture"
        ]
    elif "Multinational" in entity_type or "UN" in entity_type or "NGO" in entity_type:
        return [
            "Grant Proposal for CSOs / Local NGOs",
            "Humanitarian Emergency Relief & Aid Funding",
            "International Development & Health Initiative",
            "Strategic NGO Partnership & Joint Venture",
            "Community Sustainable Development Grant"
        ]
    elif "Legislative" in entity_type or "Ministry" in entity_type or "MDA" in entity_type:
        return [
            "Statutory Public Procurement RFP/RFQ Response",
            "Government Infrastructure & Capital Works Bid",
            "Public-Private Partnership (PPP) Proposal",
            "National Digital Identity & Access Infrastructure",
            "E-Governance & Legislative Automation Pitch"
        ]
    else:
        return [
            "Commercial Sales & Service Proposal",
            "Corporate Joint Venture & Strategic Partnership",
            "Technical Systems Architecture & Cloud Migration",
            "Enterprise Consulting & Strategic Management",
            "Unsolicited Corporate Solution Pitch"
        ]