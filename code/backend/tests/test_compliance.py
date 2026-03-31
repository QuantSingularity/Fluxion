"""
Comprehensive test suite for compliance services
Tests KYC, AML, and regulatory compliance functionality
"""

import asyncio
import base64
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from app.main import app
from fastapi.testclient import TestClient
from models.compliance import DocumentType, KYCRecord, KYCStatus
from models.user import User
from services.compliance.compliance_service import ComplianceService
from services.compliance.kyc_service import (
    BiometricVerificationResult,
    DocumentStatus,
    DocumentVerificationResult,
    KYCAssessment,
    KYCService,
    KYCTier,
    RiskRating,
)
from sqlalchemy.ext.asyncio import AsyncSession


class TestKYCService:
    """Test suite for KYC Service"""

    @pytest.fixture
    def kyc_service(self) -> Any:
        """Create KYC service instance"""
        return KYCService()

    @pytest.fixture
    def mock_db_session(self) -> Any:
        """Mock database session"""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def sample_user(self) -> Any:
        """Create sample user for testing"""
        return User(
            id=uuid4(),
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            country="US",
            phone_number="+1234567890",
            created_at=datetime.utcnow(),
        )

    @pytest.fixture
    def sample_kyc_record(self, sample_user: Any) -> Any:
        """Create sample KYC record"""
        return KYCRecord(
            id=uuid4(),
            user_id=sample_user.id,
            target_level=KYCTier.STANDARD.value,
            status=KYCStatus.PENDING,
            email_verified=True,
            phone_verified=True,
            identity_verified=False,
            address_verified=False,
            biometric_verified=False,
            created_at=datetime.utcnow(),
        )

    @pytest.fixture
    def sample_document_data(self) -> Any:
        """Create sample document data"""
        sample_image = b"fake_image_data_for_testing"
        return base64.b64encode(sample_image)

    @pytest.mark.asyncio
    async def test_initiate_kyc_process(
        self, kyc_service, mock_db_session, sample_user
    ):
        """Test KYC process initiation"""
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = (
            sample_user
        )
        mock_db_session.commit = AsyncMock()
        kyc_process = await kyc_service.initiate_kyc_process(
            mock_db_session, sample_user.id, KYCTier.STANDARD
        )
        assert "kyc_id" in kyc_process
        assert kyc_process["user_id"] == str(sample_user.id)
        assert kyc_process["target_tier"] == KYCTier.STANDARD.value
        assert "required_steps" in kyc_process
        assert "transaction_limits" in kyc_process
        assert isinstance(kyc_process["required_steps"], list)

    @pytest.mark.asyncio
    async def test_verify_document_government_id(
        self, kyc_service, mock_db_session, sample_user, sample_document_data
    ):
        """Test government ID document verification"""
        document_metadata = {
            "filename": "passport.jpg",
            "file_size": 1024000,
            "image_quality": 0.9,
        }
        with patch.object(
            kyc_service.encryption_service, "encrypt_data"
        ) as mock_encrypt:
            mock_encrypt.return_value = b"encrypted_document_data"
            verification_result = await kyc_service.verify_document(
                mock_db_session,
                sample_user.id,
                DocumentType.GOVERNMENT_ID,
                base64.b64decode(sample_document_data),
                document_metadata,
            )
            assert isinstance(verification_result, DocumentVerificationResult)
            assert verification_result.document_type == DocumentType.GOVERNMENT_ID
            assert verification_result.status in [status for status in DocumentStatus]
            assert 0 <= verification_result.confidence_score <= 1
            assert "document_number" in verification_result.extracted_data
            assert "full_name" in verification_result.extracted_data
            assert isinstance(verification_result.verification_checks, dict)
            assert verification_result.processing_time > 0

    @pytest.mark.asyncio
    async def test_verify_document_proof_of_address(
        self, kyc_service, mock_db_session, sample_user, sample_document_data
    ):
        """Test proof of address document verification"""
        document_metadata = {
            "filename": "utility_bill.pdf",
            "file_size": 512000,
            "image_quality": 0.85,
        }
        with patch.object(
            kyc_service.encryption_service, "encrypt_data"
        ) as mock_encrypt:
            mock_encrypt.return_value = b"encrypted_document_data"
            verification_result = await kyc_service.verify_document(
                mock_db_session,
                sample_user.id,
                DocumentType.PROOF_OF_ADDRESS,
                base64.b64decode(sample_document_data),
                document_metadata,
            )
            assert verification_result.document_type == DocumentType.PROOF_OF_ADDRESS
            assert "address" in verification_result.extracted_data
            assert "document_date" in verification_result.extracted_data
            assert verification_result.expires_at is not None

    @pytest.mark.asyncio
    async def test_verify_biometric(
        self, kyc_service, mock_db_session, sample_user, sample_document_data
    ):
        """Test biometric verification"""
        selfie_data = base64.b64decode(sample_document_data)
        verification_result = await kyc_service.verify_biometric(
            mock_db_session, sample_user.id, selfie_data
        )
        assert isinstance(verification_result, BiometricVerificationResult)
        assert 0 <= verification_result.match_score <= 1
        assert 0 <= verification_result.liveness_score <= 1
        assert 0 <= verification_result.quality_score <= 1
        assert isinstance(verification_result.is_match, bool)
        assert isinstance(verification_result.risk_indicators, list)
        assert verification_result.verified_at is not None

    @pytest.mark.asyncio
    async def test_perform_comprehensive_assessment(
        self, kyc_service, mock_db_session, sample_user
    ):
        """Test comprehensive KYC assessment"""
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = (
            sample_user
        )
        with patch.object(
            kyc_service, "_perform_sanctions_screening"
        ) as mock_sanctions, patch.object(
            kyc_service, "_perform_pep_screening"
        ) as mock_pep, patch.object(
            kyc_service, "_perform_adverse_media_check"
        ) as mock_media, patch.object(
            kyc_service, "_verify_address"
        ) as mock_address, patch.object(
            kyc_service, "_verify_source_of_funds"
        ) as mock_funds:
            mock_sanctions.return_value = {
                "checked": True,
                "match_found": False,
                "confidence": 0.99,
            }
            mock_pep.return_value = {
                "checked": True,
                "is_pep": False,
                "confidence": 0.95,
            }
            mock_media.return_value = {
                "checked": True,
                "adverse_findings": False,
                "confidence": 0.9,
            }
            mock_address.return_value = {"verified": True, "confidence": 0.88}
            mock_funds.return_value = {
                "verified": False,
                "documentation_provided": False,
            }
            assessment = await kyc_service.perform_comprehensive_assessment(
                mock_db_session, sample_user.id
            )
            assert isinstance(assessment, KYCAssessment)
            assert assessment.user_id == str(sample_user.id)
            assert assessment.kyc_level in [tier for tier in KYCTier]
            assert assessment.overall_status in [status for status in KYCStatus]
            assert assessment.risk_rating in [rating for rating in RiskRating]
            assert 0 <= assessment.compliance_score <= 1
            assert assessment.sanctions_check is not None
            assert assessment.pep_check is not None
            assert assessment.adverse_media_check is not None
            assert isinstance(assessment.recommendations, list)
            assert assessment.next_review_date > datetime.utcnow()

    @pytest.mark.asyncio
    async def test_sanctions_screening(self, kyc_service, sample_user):
        """Test sanctions screening functionality"""
        screening_result = await kyc_service._perform_sanctions_screening(sample_user)
        assert "checked" in screening_result
        assert "match_found" in screening_result
        assert "lists_checked" in screening_result
        assert "confidence" in screening_result
        assert screening_result["checked"] is True
        assert isinstance(screening_result["lists_checked"], list)
        assert 0 <= screening_result["confidence"] <= 1

    @pytest.mark.asyncio
    async def test_pep_screening(self, kyc_service, sample_user):
        """Test PEP (Politically Exposed Person) screening"""
        pep_result = await kyc_service._perform_pep_screening(sample_user)
        assert "checked" in pep_result
        assert "is_pep" in pep_result
        assert "confidence" in pep_result
        assert pep_result["checked"] is True
        assert isinstance(pep_result["is_pep"], bool)
        assert 0 <= pep_result["confidence"] <= 1

    @pytest.mark.asyncio
    async def test_adverse_media_check(self, kyc_service, sample_user):
        """Test adverse media screening"""
        media_result = await kyc_service._perform_adverse_media_check(sample_user)
        assert "checked" in media_result
        assert "adverse_findings" in media_result
        assert "sources_checked" in media_result
        assert "confidence" in media_result
        assert media_result["checked"] is True
        assert isinstance(media_result["adverse_findings"], bool)
        assert media_result["sources_checked"] > 0

    def test_risk_assessment_calculation(
        self, kyc_service: Any, sample_user: Any
    ) -> Any:
        """Test risk assessment calculation logic"""
        sanctions_check = {"match_found": False}
        pep_check = {"is_pep": False}
        adverse_media_check = {"adverse_findings": False}
        document_verifications = []
        biometric_verification = None
        risk_rating, compliance_score = asyncio.run(
            kyc_service._calculate_risk_assessment(
                sample_user,
                sanctions_check,
                pep_check,
                adverse_media_check,
                document_verifications,
                biometric_verification,
            )
        )
        assert risk_rating in [rating for rating in RiskRating]
        assert 0 <= compliance_score <= 1
        high_risk_user = User(
            id=uuid4(),
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            country="AF",
            created_at=datetime.utcnow(),
        )
        sanctions_check_high = {"match_found": True}
        pep_check_high = {"is_pep": True}
        risk_rating_high, compliance_score_high = asyncio.run(
            kyc_service._calculate_risk_assessment(
                high_risk_user,
                sanctions_check_high,
                pep_check_high,
                adverse_media_check,
                document_verifications,
                biometric_verification,
            )
        )
        assert risk_rating_high in [RiskRating.HIGH, RiskRating.PROHIBITED]
        assert compliance_score_high < compliance_score

    def test_kyc_tier_determination(self, kyc_service: Any) -> Any:
        """Test KYC tier determination logic"""
        basic_tier = asyncio.run(kyc_service._determine_kyc_level([], None, 0.4))
        assert basic_tier == KYCTier.BASIC
        mock_id_verification = DocumentVerificationResult(
            document_id=str(uuid4()),
            document_type=DocumentType.GOVERNMENT_ID,
            status=DocumentStatus.APPROVED,
            confidence_score=0.9,
            extracted_data={},
            verification_checks={},
            risk_indicators=[],
            processing_time=2.5,
            verified_at=datetime.utcnow(),
            expires_at=None,
        )
        standard_tier = asyncio.run(
            kyc_service._determine_kyc_level([mock_id_verification], None, 0.7)
        )
        assert standard_tier == KYCTier.STANDARD

    def test_document_confidence_calculation(self, kyc_service: Any) -> Any:
        """Test document confidence score calculation"""
        high_confidence_checks = {
            "format_valid": True,
            "not_expired": True,
            "authentic_features": True,
            "readable_text": True,
            "consistent_data": True,
            "security_features": True,
        }
        high_confidence_data = {
            "document_number": "A12345678",
            "full_name": "John Doe",
            "date_of_birth": "1990-01-01",
        }
        confidence = kyc_service._calculate_document_confidence(
            high_confidence_checks, high_confidence_data
        )
        assert 0.8 <= confidence <= 1.0
        low_confidence_checks = {
            "format_valid": False,
            "not_expired": True,
            "authentic_features": False,
            "readable_text": True,
            "consistent_data": False,
            "security_features": False,
        }
        low_confidence_data = {"document_number": "", "full_name": "John Doe"}
        low_confidence = kyc_service._calculate_document_confidence(
            low_confidence_checks, low_confidence_data
        )
        assert low_confidence < confidence

    @pytest.mark.asyncio
    async def test_document_risk_identification(self, kyc_service):
        """Test document risk identification"""
        expired_checks = {
            "not_expired": False,
            "authentic_features": True,
            "readable_text": True,
        }
        extracted_data = {"nationality": "AF"}
        risks = await kyc_service._identify_document_risks(
            extracted_data, expired_checks
        )
        assert len(risks) > 0
        assert any(("expired" in risk.lower() for risk in risks))
        assert any(("high-risk jurisdiction" in risk for risk in risks))

    @pytest.mark.asyncio
    async def test_biometric_analysis(self, kyc_service):
        """Test biometric data analysis"""
        fake_biometric_data = b"fake_biometric_image_data"
        analysis_result = await kyc_service._analyze_biometric_data(fake_biometric_data)
        assert "face_detected" in analysis_result
        assert "face_count" in analysis_result
        assert "face_quality" in analysis_result
        assert analysis_result["face_detected"] is True
        assert analysis_result["face_count"] >= 0
        assert 0 <= analysis_result["face_quality"] <= 1

    @pytest.mark.asyncio
    async def test_liveness_detection(self, kyc_service):
        """Test liveness detection"""
        fake_image_data = b"fake_image_for_liveness_test"
        liveness_score = await kyc_service._detect_liveness(fake_image_data)
        assert 0 <= liveness_score <= 1
        assert isinstance(liveness_score, float)

    @pytest.mark.asyncio
    async def test_image_quality_assessment(self, kyc_service):
        """Test image quality assessment"""
        fake_image_data = b"fake_image_for_quality_test"
        quality_score = await kyc_service._assess_image_quality(fake_image_data)
        assert 0 <= quality_score <= 1
        assert isinstance(quality_score, float)


class TestComplianceService:
    """Test suite for general Compliance Service"""

    @pytest.fixture
    def compliance_service(self) -> Any:
        """Create compliance service instance"""
        return ComplianceService()

    @pytest.fixture
    def mock_db_session(self) -> Any:
        """Mock database session"""
        return AsyncMock(spec=AsyncSession)

    @pytest.mark.asyncio
    async def test_transaction_monitoring(self, compliance_service, mock_db_session):
        """Test transaction monitoring for suspicious activity"""
        suspicious_transaction = {
            "user_id": str(uuid4()),
            "amount": Decimal("50000.00"),
            "frequency": 10,
            "country_risk": 0.8,
            "time_pattern": "unusual",
        }
        monitoring_result = await compliance_service.monitor_transaction(
            mock_db_session, suspicious_transaction
        )
        assert "risk_score" in monitoring_result
        assert "flags" in monitoring_result
        assert "recommended_action" in monitoring_result
        assert 0 <= monitoring_result["risk_score"] <= 1
        assert isinstance(monitoring_result["flags"], list)

    @pytest.mark.asyncio
    async def test_aml_screening(self, compliance_service, mock_db_session):
        """Test AML (Anti-Money Laundering) screening"""
        user_data = {
            "user_id": str(uuid4()),
            "full_name": "John Doe",
            "country": "US",
            "transaction_patterns": {
                "large_cash_transactions": 2,
                "rapid_movement": False,
                "structuring_pattern": False,
            },
        }
        aml_result = await compliance_service.perform_aml_screening(
            mock_db_session, user_data
        )
        assert "aml_risk_score" in aml_result
        assert "suspicious_indicators" in aml_result
        assert "compliance_status" in aml_result
        assert 0 <= aml_result["aml_risk_score"] <= 1
        assert isinstance(aml_result["suspicious_indicators"], list)

    @pytest.mark.asyncio
    async def test_regulatory_reporting(self, compliance_service, mock_db_session):
        """Test regulatory reporting functionality"""
        reporting_data = {
            "report_type": "SAR",
            "user_id": str(uuid4()),
            "transaction_ids": [str(uuid4()), str(uuid4())],
            "suspicious_activity": "Unusual transaction patterns",
            "jurisdiction": "US",
        }
        report_result = await compliance_service.generate_regulatory_report(
            mock_db_session, reporting_data
        )
        assert "report_id" in report_result
        assert "status" in report_result
        assert "submission_deadline" in report_result
        assert report_result["status"] in ["pending", "submitted", "filed"]

    @pytest.mark.asyncio
    async def test_compliance_alert_generation(
        self, compliance_service, mock_db_session
    ):
        """Test compliance alert generation"""
        alert_data = {
            "user_id": str(uuid4()),
            "alert_type": "high_risk_transaction",
            "severity": "high",
            "description": "Transaction exceeds risk threshold",
            "metadata": {"transaction_amount": 100000, "risk_score": 0.85},
        }
        alert_result = await compliance_service.create_compliance_alert(
            mock_db_session, alert_data
        )
        assert "alert_id" in alert_result
        assert "created_at" in alert_result
        assert "status" in alert_result
        assert alert_result["status"] == "active"

    def test_risk_scoring_algorithm(self, compliance_service: Any) -> Any:
        """Test risk scoring algorithm"""
        low_risk_factors = {
            "country_risk": 0.1,
            "transaction_amount": 1000,
            "frequency": 1,
            "kyc_level": "enhanced",
            "sanctions_match": False,
            "pep_status": False,
        }
        low_risk_score = compliance_service.calculate_risk_score(low_risk_factors)
        assert 0 <= low_risk_score <= 1
        assert low_risk_score < 0.5
        high_risk_factors = {
            "country_risk": 0.9,
            "transaction_amount": 100000,
            "frequency": 20,
            "kyc_level": "basic",
            "sanctions_match": True,
            "pep_status": True,
        }
        high_risk_score = compliance_service.calculate_risk_score(high_risk_factors)
        assert high_risk_score > low_risk_score
        assert high_risk_score > 0.7

    def test_transaction_pattern_analysis(self, compliance_service: Any) -> Any:
        """Test transaction pattern analysis"""
        normal_transactions = [
            {"amount": 1000, "timestamp": datetime.utcnow() - timedelta(days=i)}
            for i in range(30)
        ]
        normal_analysis = compliance_service.analyze_transaction_patterns(
            normal_transactions
        )
        assert "pattern_type" in normal_analysis
        assert "risk_indicators" in normal_analysis
        assert normal_analysis["pattern_type"] == "normal"
        structuring_transactions = [
            {"amount": 9500, "timestamp": datetime.utcnow() - timedelta(hours=i)}
            for i in range(10)
        ]
        suspicious_analysis = compliance_service.analyze_transaction_patterns(
            structuring_transactions
        )
        assert suspicious_analysis["pattern_type"] == "suspicious"
        assert len(suspicious_analysis["risk_indicators"]) > 0

    def test_jurisdiction_compliance_rules(self, compliance_service: Any) -> Any:
        """Test jurisdiction-specific compliance rules"""
        us_rules = compliance_service.get_jurisdiction_rules("US")
        assert "transaction_reporting_threshold" in us_rules
        assert "kyc_requirements" in us_rules
        assert "sanctions_lists" in us_rules
        assert us_rules["transaction_reporting_threshold"] == 10000
        eu_rules = compliance_service.get_jurisdiction_rules("EU")
        assert "gdpr_compliance" in eu_rules
        assert "mld5_requirements" in eu_rules
        assert eu_rules["gdpr_compliance"] is True


class TestComplianceAPI:
    """Test suite for Compliance API endpoints"""

    @pytest.fixture
    def client(self) -> Any:
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self) -> Any:
        """Mock authentication headers"""
        return {"Authorization": "Bearer test_token"}

    def test_initiate_kyc_endpoint(self, client: Any, auth_headers: Any) -> Any:
        """Test POST /api/v1/kyc/initiate endpoint"""
        user_id = str(uuid4())
        with patch("services.compliance.kyc_service.KYCService") as mock_service:
            mock_service.return_value.initiate_kyc_process.return_value = {
                "kyc_id": str(uuid4()),
                "user_id": user_id,
                "target_tier": "standard",
                "required_steps": [],
            }
            response = client.post(
                "/api/v1/kyc/initiate",
                json={"user_id": user_id, "target_tier": "standard"},
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == user_id
            assert "kyc_id" in data

    def test_upload_kyc_document_endpoint(self, client: Any, auth_headers: Any) -> Any:
        """Test POST /api/v1/kyc/document endpoint"""
        user_id = str(uuid4())
        files = {"document": ("passport.jpg", b"fake_image_data", "image/jpeg")}
        data = {"user_id": user_id, "document_type": "government_id"}
        with patch("services.compliance.kyc_service.KYCService") as mock_service:
            mock_service.return_value.verify_document.return_value = (
                DocumentVerificationResult(
                    document_id=str(uuid4()),
                    document_type=DocumentType.GOVERNMENT_ID,
                    status=DocumentStatus.APPROVED,
                    confidence_score=0.95,
                    extracted_data={},
                    verification_checks={},
                    risk_indicators=[],
                    processing_time=2.5,
                    verified_at=datetime.utcnow(),
                    expires_at=None,
                )
            )
            response = client.post(
                "/api/v1/kyc/document", files=files, data=data, headers=auth_headers
            )
            assert response.status_code == 200
            response_data = response.json()
            assert "document_id" in response_data
            assert response_data["status"] == "approved"

    def test_get_compliance_status_endpoint(
        self, client: Any, auth_headers: Any
    ) -> Any:
        """Test GET /api/v1/compliance/status endpoint"""
        user_id = str(uuid4())
        with patch("services.compliance.kyc_service.KYCService") as mock_service:
            mock_service.return_value.perform_comprehensive_assessment.return_value = (
                KYCAssessment(
                    user_id=user_id,
                    kyc_level=KYCTier.STANDARD,
                    overall_status=KYCStatus.APPROVED,
                    risk_rating=RiskRating.LOW,
                    compliance_score=0.85,
                    document_verifications=[],
                    biometric_verification=None,
                    sanctions_check={},
                    pep_check={},
                    adverse_media_check={},
                    address_verification={},
                    source_of_funds_verification={},
                    ongoing_monitoring={},
                    recommendations=[],
                    next_review_date=datetime.utcnow() + timedelta(days=90),
                    assessed_at=datetime.utcnow(),
                )
            )
            response = client.get(
                f"/api/v1/compliance/status?user_id={user_id}", headers=auth_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == user_id
            assert "compliance_score" in data
            assert "kyc_level" in data

    def test_submit_biometric_endpoint(self, client: Any, auth_headers: Any) -> Any:
        """Test POST /api/v1/kyc/biometric endpoint"""
        user_id = str(uuid4())
        files = {"selfie": ("selfie.jpg", b"fake_selfie_data", "image/jpeg")}
        data = {"user_id": user_id}
        with patch("services.compliance.kyc_service.KYCService") as mock_service:
            mock_service.return_value.verify_biometric.return_value = (
                BiometricVerificationResult(
                    verification_id=str(uuid4()),
                    match_score=0.92,
                    liveness_score=0.88,
                    quality_score=0.85,
                    is_match=True,
                    risk_indicators=[],
                    verified_at=datetime.utcnow(),
                )
            )
            response = client.post(
                "/api/v1/kyc/biometric", files=files, data=data, headers=auth_headers
            )
            assert response.status_code == 200
            response_data = response.json()
            assert "verification_id" in response_data
            assert response_data["is_match"] is True
            assert "match_score" in response_data


class TestComplianceIntegration:
    """Integration tests for compliance services"""

    @pytest.mark.asyncio
    async def test_end_to_end_kyc_process(self):
        """Test complete KYC process from initiation to completion"""
        kyc_service = EnhancedKYCService()
        mock_db = AsyncMock()
        user = User(
            id=uuid4(),
            email="integration@test.com",
            first_name="Integration",
            last_name="Test",
            country="US",
        )
        mock_db.execute.return_value.scalar_one_or_none.return_value = user
        mock_db.commit = AsyncMock()
        kyc_process = await kyc_service.initiate_kyc_process(
            mock_db, user.id, KYCTier.ENHANCED
        )
        assert kyc_process["target_tier"] == KYCTier.ENHANCED.value
        with patch.object(kyc_service.encryption_service, "encrypt_data"):
            doc_result = await kyc_service.verify_document(
                mock_db,
                user.id,
                DocumentType.GOVERNMENT_ID,
                b"fake_document_data",
                {"filename": "id.jpg"},
            )
            assert doc_result.status in [
                DocumentStatus.APPROVED,
                DocumentStatus.REQUIRES_REVIEW,
            ]
        bio_result = await kyc_service.verify_biometric(
            mock_db, user.id, b"fake_selfie_data"
        )
        assert isinstance(bio_result.is_match, bool)
        with patch.object(kyc_service, "_perform_sanctions_screening"), patch.object(
            kyc_service, "_perform_pep_screening"
        ), patch.object(kyc_service, "_perform_adverse_media_check"), patch.object(
            kyc_service, "_verify_address"
        ), patch.object(
            kyc_service, "_verify_source_of_funds"
        ):
            assessment = await kyc_service.perform_comprehensive_assessment(
                mock_db, user.id
            )
            assert isinstance(assessment, KYCAssessment)
            assert assessment.user_id == str(user.id)

    def test_compliance_workflow_validation(self) -> Any:
        """Test compliance workflow validation"""
        compliance_service = ComplianceService()
        valid_workflow = {
            "kyc_completion": True,
            "document_verification": True,
            "biometric_verification": True,
            "sanctions_screening": True,
            "risk_assessment": "low",
        }
        validation_result = compliance_service.validate_compliance_workflow(
            valid_workflow
        )
        assert validation_result["is_valid"] is True
        assert len(validation_result["missing_steps"]) == 0
        invalid_workflow = {
            "kyc_completion": False,
            "document_verification": False,
            "sanctions_screening": False,
        }
        invalid_result = compliance_service.validate_compliance_workflow(
            invalid_workflow
        )
        assert invalid_result["is_valid"] is False
        assert len(invalid_result["missing_steps"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
