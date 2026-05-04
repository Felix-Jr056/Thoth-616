"""
Seed test data for Synthesis Service testing.
Run once before calling POST /synthesis with interview_id='interview_test_001'
"""
from app.dependencies import interview_repo

async def seed():
    # Create interview record
    interview = await interview_repo.create(
        sme_id="sme_test_001",
        topic="Customer Data Privacy and Regulatory Compliance"
    )
    interview_id = "interview_test_001"
    agenda = [
        "Customer data collection scope and legal basis",
        "Data Subject Request handling process",
        "Consent management and opt-out workflows",
        "Data breach response and notification",
        "Cross-border data transfer",
        "Privacy Impact Assessments",
        "Data retention and deletion policies",
        "Law enforcement data requests",
        "Third-party vendor data governance",
        "Children's data and age verification",
    ]
    interview_repo._interviews[interview_id] = {
        "id": interview_id,
        "sme_id": "sme_test_001",
        "topic": "Customer Data Privacy and Regulatory Compliance",
        "status": "completed",
        "agenda": agenda,
    }

    # Seed 10 topic summaries
    topic_summaries = [
        {
            "topic_index": 0,
            "topic_question": "What types of customer data does T-Mobile collect, and what is the legal basis for collecting each type?",
            "refined_content": """T-Mobile collects four categories of customer data: account data (name, address, SSN last four digits, billing info) under contractual necessity; network usage data including location under legitimate interest and CALEA obligations; marketing and behavioral data under consent with opt-in required for sensitive uses; and customer service interaction data under legitimate interest. Precise geolocation is sensitive personal information under CPRA requiring explicit opt-in consent for any use beyond service delivery. A data purpose tagging system in the CDP enforces permitted use cases at the pipeline level and blocks unauthorized use. Derived data — where combining non-sensitive fields produces sensitive inferences such as location profiles — is an unresolved compliance edge case. The California Privacy Protection Agency has not issued clear guidance on derived data. T-Mobile policy requires PIA review for any ML model combining more than two data categories. Intermediate outputs from such models must be deleted post-training or tagged and controlled as sensitive personal information."""
        },
        {
            "topic_index": 1,
            "topic_question": "Walk me through how T-Mobile handles a Data Subject Request from submission to final fulfillment.",
            "refined_content": """T-Mobile's DSR portal supports access, deletion, correction, and opt-out of sale/sharing requests, accessible via T-Mobile.com and the app. Identity verification is required before fulfillment. The fulfillment system queries 14 internal systems including billing, network, CRM, marketing platforms, the CDP, and legacy systems. Three legacy pre-merger systems are not integrated and require manual deletion tickets — a known material compliance gap documented by CPRA counsel. Deletions are processed in monthly batch cycles with legal hold checks applied before execution. Response window is 45 days with a possible 45-day extension with customer notification. Three customer escalations in 18 months were caused by incomplete legacy deletions resulting in re-marketing after deletion requests; documented as near-misses with no regulatory notifications issued. A data governance platform is in procurement targeting Q3 next year to provide unified data inventory across all systems."""
        },
        {
            "topic_index": 2,
            "topic_question": "How does T-Mobile manage customer consent across its different data use cases, and what happens operationally when a customer opts out?",
            "refined_content": """Consent is managed through a dedicated Consent Management System with four categories: essential service (no opt-out), operational communications (default on, opt-out available), marketing communications (default on for existing customers, opt-in required for new CPRA customers), and third-party data sharing (default off for California residents). Consent changes propagate via event stream with up to 24-hour lag for batch systems — a disclosed compliance risk. Customers moving to California automatically receive CPRA defaults via nightly address sync, with up to a 24-hour gap before new defaults apply. T-Mobile applies CPRA rules to all customers with California billing addresses regardless of service address, a conservative interpretation approved by legal. Targeted advertising opt-out rates among California customers exceed 60% since CPRA, impacting advertising revenue. An unresolved internal debate exists over whether quality assurance call recording requires consent or qualifies as legitimate interest."""
        },
        {
            "topic_index": 3,
            "topic_question": "Walk me through T-Mobile's data breach response process, including who gets notified, in what timeframe, and what the key decision points are.",
            "refined_content": """T-Mobile's breach response follows a five-phase IR plan: detection/triage (privacy and legal notified within 24 hours of detection), containment, investigation, notification, and remediation. Notification timelines vary by regulation: 30 days under California law, 30 days for CPNI breaches under FCC rules, 4 business days for material breaches under SEC rules. Encrypted data may qualify for notification safe harbor. The 2021 breach exposed three process failures: production data in testing environments, inadequate monitoring of non-production systems, and incomplete data inventory. Post-breach remediation includes: prohibition on production data in non-production environments, synthetic data generation for testing, universal environment monitoring, and mandatory data inventory for any environment processing personal data. A 20-year FTC consent decree requires annual third-party privacy audits (~$2M/year), annual compliance reports, and FTC access rights. Major data practice changes require outside counsel review against consent decree terms."""
        },
        {
            "topic_index": 4,
            "topic_question": "How does T-Mobile handle customer data that needs to move across international borders?",
            "refined_content": """T-Mobile US faces three cross-border transfer scenarios. Data flows to parent company Deutsche Telekom (Germany) are governed by GDPR and use Standard Contractual Clauses with supplementary measures including encryption, access controls, and prohibition on combining T-Mobile US customer data with other DT market data. Post-Schrems II, some DT flows were reclassified as non-personal after anonymization review; a joint cloud environment with DT was separated at approximately $4M cost due to transfer risk. Offshore vendor access in Philippines, India, and Mexico is governed by DPAs and transfer impact assessments. A four-tier data classification policy (public/internal/confidential/restricted) prohibits offshore vendor access to restricted-tier data (SSNs, financial accounts, precise location, health data), enforced technically not just contractually. Redesigning customer service workflows to route restricted-data scenarios to domestic agents took six months. International roaming involves customer data touching foreign network operators, covered by roaming agreements and operationally necessary."""
        },
        {
            "topic_index": 5,
            "topic_question": "How does T-Mobile's PIA process work, and what kinds of projects actually get blocked or significantly changed as a result?",
            "refined_content": """PIAs are triggered by new or significantly changed data practices including new products, vendors, internal tools, and changes to data flows. A preliminary questionnaire determines whether a full PIA or lighter review is sufficient. Full PIAs are mandatory for sensitive personal information, large-scale profiling, and automated decision-making with significant effects. PIAs result in significant project changes in approximately 30-40% of cases and full project blocks in approximately 5% of cases. Notable examples: a churn prediction model was delayed four months to redesign the pipeline after a PIA identified that intermediate outputs created precise location profiles; a third-party data enrichment partnership was blocked because the enrichment would create inferences about financial vulnerability with no adequate mitigations; a CLV scoring system was redesigned to remove undisclosed data elements rather than update the privacy notice. Organizational resistance exists from product and marketing teams due to 2-4 week timeline impact. Some teams have attempted to mischaracterize projects to avoid PIA triggers. Privacy reviews are being shifted earlier to the concept stage to reduce friction."""
        },
        {
            "topic_index": 6,
            "topic_question": "What are T-Mobile's data retention policies, and how are retention schedules actually enforced technically?",
            "refined_content": """Retention schedules by data category: call detail records (18 months standard, up to 7 years under legal hold), billing data (billing cycle plus 12 months for dispute resolution), customer account data (relationship duration plus 7 years post-account closure), marketing behavioral data (3 years or opt-out whichever occurs first), quality assurance call recordings (90 days). Technical enforcement is inconsistent: automated deletion jobs exist for structured data in core systems; unstructured data and legacy systems have weak or no automated enforcement. Overretention is a known compliance liability — two documented incidents: marketing segmentation data outside retention window discovered in litigation; a regulatory inquiry involved producing data outside the stated retention period, requiring explanation of technical control gaps to the regulator. An 18-month data minimization program is underway to close the gap between policy and technical enforcement across all systems."""
        },
        {
            "topic_index": 7,
            "topic_question": "How does T-Mobile handle government and law enforcement requests for customer data?",
            "refined_content": """Law enforcement requests are processed by a dedicated Legal Response team separate from privacy. Standard process: validate legal sufficiency (jurisdiction, legal process, scope), fulfill within required scope only without volunteering additional data. Emergency requests require written agency certification but use an expedited review process. CALEA requires T-Mobile to maintain technical lawful intercept capability; actual interception requires a court order. Annual transparency reports publish aggregate request counts by type. NSLs carry mandatory non-disclosure requirements preventing customer notification. Non-NSL requests trigger customer notification where legally permitted unless restricted. T-Mobile regularly challenges technically deficient requests and has negotiated narrowed scope on overbroad requests. Challenge posture has increased post-2021 breach. No challenges have reached adversarial proceedings; all resolved through correspondence."""
        },
        {
            "topic_index": 8,
            "topic_question": "How does T-Mobile govern the privacy and data security practices of its third-party vendors who handle customer data?",
            "refined_content": """Vendor governance begins at procurement with risk-tiered review (high/medium/low). High-risk vendors require full assessment including SOC 2 review. All vendors sign a non-negotiable DPA covering permitted uses, security requirements, 48-hour breach notification, data return/deletion at contract end, and audit rights. Annual reassessment for high-risk vendors. Fourth-party subprocessor risk is a known limitation — contractual flow-down required but audit visibility is limited. Two cases of multi-week breach notification delays created downstream compliance pressure. One smaller vendor terminated for material breach of notification obligation. A larger critical vendor received a remediation plan instead of termination (independent audit plus quarterly security check-ins), reflecting practical limits of enforcement against embedded vendors."""
        },
        {
            "topic_index": 9,
            "topic_question": "How does T-Mobile handle data from customers who may be minors, and what special protections apply?",
            "refined_content": """T-Mobile's primary COPPA mitigation is the contractual requirement for an adult account holder — minor lines are sub-accounts with implied parental consent. Age verification relies entirely on account holder attestation; no technical age verification exists. All sub-accounts on family plans are excluded from behavioral advertising targeting regardless of verified age. California AADC compliance is in progress: DPIAs required for all consumer-facing digital services likely accessed by minors, default highest-privacy settings required, profiling of minors restricted. Several personalization algorithms have been disabled for family plan sub-accounts. AI-powered features (recommendations, usage insights, predictive tools) each require individual AADC evaluation — work ongoing. AADC compliance framework is being designed as a multi-state baseline."""
        }
    ]

    for summary in topic_summaries:
        await interview_repo.save_topic_summary(
            interview_id=interview_id,
            topic_index=summary["topic_index"],
            topic_question=summary["topic_question"],
            refined_content=summary["refined_content"],
        )

    print(f"Seeded interview_id: {interview_id} with 10 topic summaries.")
    print("Now call: POST /synthesis with interview_id='interview_test_001'")


if __name__ == "__main__":
    import asyncio
    asyncio.run(seed())
