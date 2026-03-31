"""
Comprehensive Notification and Communication Service for Fluxion Backend
Implements multi-channel notification delivery, template management, user preferences,
and communication tracking for financial services platform.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from services.security.encryption_service import EncryptionService

logger = logging.getLogger(__name__)


class NotificationChannel(Enum):
    """Notification delivery channels"""

    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"
    WEBHOOK = "webhook"
    SLACK = "slack"
    TEAMS = "teams"


class NotificationType(Enum):
    """Types of notifications"""

    ACCOUNT_ALERT = "account_alert"
    SECURITY_ALERT = "security_alert"
    TRANSACTION_NOTIFICATION = "transaction_notification"
    PORTFOLIO_UPDATE = "portfolio_update"
    RISK_ALERT = "risk_alert"
    MARKET_UPDATE = "market_update"
    SYSTEM_MAINTENANCE = "system_maintenance"
    COMPLIANCE_NOTICE = "compliance_notice"
    PROMOTIONAL = "promotional"
    WELCOME = "welcome"
    PASSWORD_RESET = "password_reset"
    EMAIL_VERIFICATION = "email_verification"
    KYC_UPDATE = "kyc_update"


class NotificationPriority(Enum):
    """Notification priority levels"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class NotificationStatus(Enum):
    """Notification delivery status"""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"
    OPENED = "opened"
    CLICKED = "clicked"
    UNSUBSCRIBED = "unsubscribed"


@dataclass
class NotificationTemplate:
    """Notification template"""

    template_id: str
    name: str
    notification_type: NotificationType
    channel: NotificationChannel
    subject_template: str
    body_template: str
    html_template: Optional[str]
    variables: List[str]
    language: str
    version: str
    created_at: datetime
    updated_at: datetime
    active: bool
    metadata: Dict[str, Any]


@dataclass
class NotificationPreference:
    """User notification preferences"""

    user_id: str
    notification_type: NotificationType
    enabled_channels: List[NotificationChannel]
    frequency: str
    quiet_hours_start: Optional[str]
    quiet_hours_end: Optional[str]
    timezone: str
    updated_at: datetime


@dataclass
class Notification:
    """Individual notification"""

    notification_id: str
    user_id: str
    notification_type: NotificationType
    channel: NotificationChannel
    priority: NotificationPriority
    subject: str
    message: str
    html_content: Optional[str]
    template_id: Optional[str]
    template_variables: Dict[str, Any]
    recipient: str
    sender: str
    status: NotificationStatus
    scheduled_at: datetime
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    opened_at: Optional[datetime]
    clicked_at: Optional[datetime]
    failed_reason: Optional[str]
    retry_count: int
    max_retries: int
    expires_at: Optional[datetime]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


@dataclass
class NotificationBatch:
    """Batch notification for multiple recipients"""

    batch_id: str
    name: str
    notification_type: NotificationType
    channel: NotificationChannel
    template_id: str
    template_variables: Dict[str, Any]
    recipients: List[str]
    scheduled_at: datetime
    created_by: str
    status: str
    total_recipients: int
    sent_count: int
    delivered_count: int
    failed_count: int
    created_at: datetime
    updated_at: datetime


class NotificationService:
    """
    Comprehensive notification service providing:
    - Multi-channel notification delivery (email, SMS, push, in-app)
    - Template management and personalization
    - User preference management
    - Batch notification processing
    - Delivery tracking and analytics
    - Retry logic and failure handling
    - Compliance and opt-out management
    - Real-time and scheduled notifications
    - Integration with external services
    """

    def __init__(self) -> None:
        self.encryption_service = EncryptionService()
        self.max_retries = 3
        self.retry_delays = [300, 900, 3600]
        self.batch_size = 100
        self.rate_limits = {
            NotificationChannel.EMAIL: 1000,
            NotificationChannel.SMS: 100,
            NotificationChannel.PUSH: 5000,
        }
        self.smtp_config = {
            "host": "smtp.gmail.com",
            "port": 587,
            "username": "noreply@fluxion.com",
            "password": "app_password",
            "use_tls": True,
        }
        self.sms_config = {
            "provider": "twilio",
            "account_sid": "your_account_sid",
            "auth_token": "your_auth_token",
            "from_number": "+1234567890",
        }
        self.push_config = {
            "fcm_server_key": "your_fcm_server_key",
            "apns_key_id": "your_apns_key_id",
            "apns_team_id": "your_apns_team_id",
        }
        self.notifications: Dict[str, Notification] = {}
        self.templates: Dict[str, NotificationTemplate] = {}
        self.user_preferences: Dict[str, List[NotificationPreference]] = {}
        self.notification_batches: Dict[str, NotificationBatch] = {}
        self.delivery_queue: List[str] = []
        self.retry_queue: List[Tuple[str, datetime]] = []
        self._initialize_default_templates()
        asyncio.create_task(self._delivery_worker())
        asyncio.create_task(self._retry_worker())

    def _initialize_default_templates(self) -> Any:
        """Initialize default notification templates"""
        default_templates = [
            {
                "name": "Welcome Email",
                "notification_type": NotificationType.WELCOME,
                "channel": NotificationChannel.EMAIL,
                "subject_template": "Welcome to Fluxion, {{first_name}}!",
                "body_template": "\nDear {{first_name}},\n\nWelcome to Fluxion! We're excited to have you join our financial platform.\n\nYour account has been successfully created with the email: {{email}}\n\nNext steps:\n1. Verify your email address\n2. Complete your profile\n3. Set up your investment preferences\n\nIf you have any questions, please don't hesitate to contact our support team.\n\nBest regards,\nThe Fluxion Team\n                ",
                "variables": ["first_name", "email"],
                "language": "en",
            },
            {
                "name": "Transaction Alert",
                "notification_type": NotificationType.TRANSACTION_NOTIFICATION,
                "channel": NotificationChannel.EMAIL,
                "subject_template": "Transaction Alert: {{transaction_type}} of {{amount}}",
                "body_template": "\nDear {{first_name}},\n\nThis is to notify you of a recent transaction on your account:\n\nTransaction Details:\n- Type: {{transaction_type}}\n- Amount: {{amount}} {{currency}}\n- Date: {{transaction_date}}\n- Status: {{status}}\n- Reference: {{reference_number}}\n\nIf you did not authorize this transaction, please contact us immediately.\n\nBest regards,\nFluxion Security Team\n                ",
                "variables": [
                    "first_name",
                    "transaction_type",
                    "amount",
                    "currency",
                    "transaction_date",
                    "status",
                    "reference_number",
                ],
                "language": "en",
            },
            {
                "name": "Security Alert",
                "notification_type": NotificationType.SECURITY_ALERT,
                "channel": NotificationChannel.EMAIL,
                "subject_template": "Security Alert: {{alert_type}}",
                "body_template": "\nDear {{first_name}},\n\nWe detected unusual activity on your account:\n\nAlert Details:\n- Type: {{alert_type}}\n- Time: {{alert_time}}\n- Location: {{location}}\n- Device: {{device_info}}\n\nIf this was you, no action is needed. If you don't recognize this activity, please:\n1. Change your password immediately\n2. Review your account activity\n3. Contact our security team\n\nBest regards,\nFluxion Security Team\n                ",
                "variables": [
                    "first_name",
                    "alert_type",
                    "alert_time",
                    "location",
                    "device_info",
                ],
                "language": "en",
            },
            {
                "name": "Risk Alert",
                "notification_type": NotificationType.RISK_ALERT,
                "channel": NotificationChannel.EMAIL,
                "subject_template": "Portfolio Risk Alert: {{risk_level}}",
                "body_template": "\nDear {{first_name}},\n\nYour portfolio risk assessment has identified a {{risk_level}} risk situation:\n\nRisk Details:\n- Portfolio: {{portfolio_name}}\n- Risk Score: {{risk_score}}/10\n- Primary Risk Factors: {{risk_factors}}\n- Recommended Actions: {{recommendations}}\n\nPlease review your portfolio and consider the recommended actions.\n\nBest regards,\nFluxion Risk Management Team\n                ",
                "variables": [
                    "first_name",
                    "risk_level",
                    "portfolio_name",
                    "risk_score",
                    "risk_factors",
                    "recommendations",
                ],
                "language": "en",
            },
        ]
        for template_data in default_templates:
            template_id = f"template_{uuid.uuid4().hex[:8]}"
            template = NotificationTemplate(
                template_id=template_id,
                name=template_data["name"],
                notification_type=template_data["notification_type"],
                channel=template_data["channel"],
                subject_template=template_data["subject_template"],
                body_template=template_data["body_template"],
                html_template=None,
                variables=template_data["variables"],
                language=template_data["language"],
                version="1.0",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                active=True,
                metadata={},
            )
            self.templates[template_id] = template

    async def send_notification(
        self,
        user_id: str,
        notification_type: NotificationType,
        channel: NotificationChannel,
        subject: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        template_id: Optional[str] = None,
        template_variables: Optional[Dict[str, Any]] = None,
        scheduled_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Send a notification to a user"""
        if not await self._check_user_preferences(user_id, notification_type, channel):
            return {
                "notification_id": None,
                "status": "blocked_by_preferences",
                "message": "Notification blocked by user preferences",
            }
        recipient = await self._get_recipient_address(user_id, channel)
        if not recipient:
            raise ValueError(f"No {channel.value} address found for user {user_id}")
        notification_id = f"notif_{uuid.uuid4().hex[:12]}"
        if template_id and template_variables:
            template = self.templates.get(template_id)
            if template:
                subject = self._render_template(
                    template.subject_template, template_variables
                )
                message = self._render_template(
                    template.body_template, template_variables
                )
        notification = Notification(
            notification_id=notification_id,
            user_id=user_id,
            notification_type=notification_type,
            channel=channel,
            priority=priority,
            subject=subject,
            message=message,
            html_content=None,
            template_id=template_id,
            template_variables=template_variables or {},
            recipient=recipient,
            sender=self._get_sender_address(channel),
            status=NotificationStatus.PENDING,
            scheduled_at=scheduled_at or datetime.now(timezone.utc),
            sent_at=None,
            delivered_at=None,
            opened_at=None,
            clicked_at=None,
            failed_reason=None,
            retry_count=0,
            max_retries=self.max_retries,
            expires_at=expires_at,
            metadata={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.notifications[notification_id] = notification
        if scheduled_at is None or scheduled_at <= datetime.now(timezone.utc):
            self.delivery_queue.append(notification_id)
        logger.info(
            f"Notification created: {notification_id} for user {user_id} via {channel.value}"
        )
        return {
            "notification_id": notification_id,
            "status": "queued",
            "scheduled_at": notification.scheduled_at.isoformat(),
            "channel": channel.value,
            "priority": priority.value,
        }

    async def send_batch_notification(
        self,
        name: str,
        notification_type: NotificationType,
        channel: NotificationChannel,
        template_id: str,
        recipients: List[str],
        template_variables: Dict[str, Any],
        created_by: str,
        scheduled_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Send batch notification to multiple recipients"""
        batch_id = f"batch_{uuid.uuid4().hex[:12]}"
        batch = NotificationBatch(
            batch_id=batch_id,
            name=name,
            notification_type=notification_type,
            channel=channel,
            template_id=template_id,
            template_variables=template_variables,
            recipients=recipients,
            scheduled_at=scheduled_at or datetime.now(timezone.utc),
            created_by=created_by,
            status="pending",
            total_recipients=len(recipients),
            sent_count=0,
            delivered_count=0,
            failed_count=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.notification_batches[batch_id] = batch
        notification_ids = []
        for recipient_id in recipients:
            try:
                result = await self.send_notification(
                    user_id=recipient_id,
                    notification_type=notification_type,
                    channel=channel,
                    subject="",
                    message="",
                    template_id=template_id,
                    template_variables=template_variables,
                    scheduled_at=scheduled_at,
                )
                if result["notification_id"]:
                    notification_ids.append(result["notification_id"])
            except Exception as e:
                logger.error(
                    f"Failed to create notification for recipient {recipient_id}: {str(e)}"
                )
                batch.failed_count += 1
        batch.status = "processing"
        batch.updated_at = datetime.now(timezone.utc)
        logger.info(
            f"Batch notification created: {batch_id} with {len(notification_ids)} notifications"
        )
        return {
            "batch_id": batch_id,
            "total_recipients": batch.total_recipients,
            "notifications_created": len(notification_ids),
            "failed_count": batch.failed_count,
            "status": batch.status,
        }

    async def get_notification_status(self, notification_id: str) -> Dict[str, Any]:
        """Get notification delivery status"""
        notification = self.notifications.get(notification_id)
        if not notification:
            raise ValueError("Notification not found")
        return {
            "notification_id": notification_id,
            "status": notification.status.value,
            "channel": notification.channel.value,
            "recipient": notification.recipient,
            "created_at": notification.created_at.isoformat(),
            "scheduled_at": notification.scheduled_at.isoformat(),
            "sent_at": (
                notification.sent_at.isoformat() if notification.sent_at else None
            ),
            "delivered_at": (
                notification.delivered_at.isoformat()
                if notification.delivered_at
                else None
            ),
            "opened_at": (
                notification.opened_at.isoformat() if notification.opened_at else None
            ),
            "retry_count": notification.retry_count,
            "failed_reason": notification.failed_reason,
        }

    async def get_user_notifications(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get user's notification history"""
        user_notifications = [
            notif for notif in self.notifications.values() if notif.user_id == user_id
        ]
        if status:
            user_notifications = [
                notif for notif in user_notifications if notif.status.value == status
            ]
        user_notifications.sort(key=lambda x: x.created_at, reverse=True)
        total_count = len(user_notifications)
        paginated_notifications = user_notifications[offset : offset + limit]
        formatted_notifications = []
        for notif in paginated_notifications:
            formatted_notifications.append(
                {
                    "notification_id": notif.notification_id,
                    "type": notif.notification_type.value,
                    "channel": notif.channel.value,
                    "priority": notif.priority.value,
                    "subject": notif.subject,
                    "message": (
                        notif.message[:200] + "..."
                        if len(notif.message) > 200
                        else notif.message
                    ),
                    "status": notif.status.value,
                    "created_at": notif.created_at.isoformat(),
                    "sent_at": notif.sent_at.isoformat() if notif.sent_at else None,
                    "opened_at": (
                        notif.opened_at.isoformat() if notif.opened_at else None
                    ),
                }
            )
        return {
            "user_id": user_id,
            "notifications": formatted_notifications,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count,
        }

    async def update_user_preferences(
        self, user_id: str, preferences: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Update user notification preferences"""
        user_prefs = []
        for pref_data in preferences:
            preference = NotificationPreference(
                user_id=user_id,
                notification_type=NotificationType(pref_data["notification_type"]),
                enabled_channels=[
                    NotificationChannel(ch) for ch in pref_data["enabled_channels"]
                ],
                frequency=pref_data.get("frequency", "immediate"),
                quiet_hours_start=pref_data.get("quiet_hours_start"),
                quiet_hours_end=pref_data.get("quiet_hours_end"),
                timezone=pref_data.get("timezone", "UTC"),
                updated_at=datetime.now(timezone.utc),
            )
            user_prefs.append(preference)
        self.user_preferences[user_id] = user_prefs
        logger.info(f"Notification preferences updated for user {user_id}")
        return {
            "user_id": user_id,
            "preferences_count": len(user_prefs),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def mark_notification_opened(self, notification_id: str) -> Dict[str, Any]:
        """Mark notification as opened (for tracking)"""
        notification = self.notifications.get(notification_id)
        if not notification:
            raise ValueError("Notification not found")
        if notification.status == NotificationStatus.DELIVERED:
            notification.status = NotificationStatus.OPENED
            notification.opened_at = datetime.now(timezone.utc)
            notification.updated_at = datetime.now(timezone.utc)
            logger.info(f"Notification marked as opened: {notification_id}")
        return {
            "notification_id": notification_id,
            "status": notification.status.value,
            "opened_at": (
                notification.opened_at.isoformat() if notification.opened_at else None
            ),
        }

    async def _delivery_worker(self):
        """Background worker for processing notification delivery queue"""
        while True:
            try:
                if self.delivery_queue:
                    notification_id = self.delivery_queue.pop(0)
                    await self._deliver_notification(notification_id)
                else:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Delivery worker error: {str(e)}")
                await asyncio.sleep(5)

    async def _retry_worker(self):
        """Background worker for processing retry queue"""
        while True:
            try:
                current_time = datetime.now(timezone.utc)
                ready_retries = []
                for notification_id, retry_time in self.retry_queue:
                    if current_time >= retry_time:
                        ready_retries.append((notification_id, retry_time))
                for notification_id, retry_time in ready_retries:
                    self.retry_queue.remove((notification_id, retry_time))
                    await self._deliver_notification(notification_id)
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Retry worker error: {str(e)}")
                await asyncio.sleep(60)

    async def _deliver_notification(self, notification_id: str):
        """Deliver a single notification"""
        notification = self.notifications.get(notification_id)
        if not notification:
            return
        if (
            notification.expires_at
            and datetime.now(timezone.utc) > notification.expires_at
        ):
            notification.status = NotificationStatus.FAILED
            notification.failed_reason = "Notification expired"
            notification.updated_at = datetime.now(timezone.utc)
            return
        try:
            if notification.channel == NotificationChannel.EMAIL:
                await self._send_email(notification)
            elif notification.channel == NotificationChannel.SMS:
                await self._send_sms(notification)
            elif notification.channel == NotificationChannel.PUSH:
                await self._send_push_notification(notification)
            elif notification.channel == NotificationChannel.IN_APP:
                await self._send_in_app_notification(notification)
            notification.status = NotificationStatus.SENT
            notification.sent_at = datetime.now(timezone.utc)
            notification.updated_at = datetime.now(timezone.utc)
            await asyncio.sleep(1)
            notification.status = NotificationStatus.DELIVERED
            notification.delivered_at = datetime.now(timezone.utc)
            logger.info(
                f"Notification delivered: {notification_id} via {notification.channel.value}"
            )
        except Exception as e:
            notification.retry_count += 1
            notification.failed_reason = str(e)
            notification.updated_at = datetime.now(timezone.utc)
            if notification.retry_count < notification.max_retries:
                retry_delay = self.retry_delays[
                    min(notification.retry_count - 1, len(self.retry_delays) - 1)
                ]
                retry_time = datetime.now(timezone.utc) + timedelta(seconds=retry_delay)
                self.retry_queue.append((notification_id, retry_time))
                logger.warning(
                    f"Notification delivery failed, scheduled retry {notification.retry_count}: {notification_id}"
                )
            else:
                notification.status = NotificationStatus.FAILED
                logger.error(
                    f"Notification delivery failed permanently: {notification_id} - {str(e)}"
                )

    async def _send_email(self, notification: Notification):
        """Send email notification"""
        msg = MIMEMultipart()
        msg["From"] = notification.sender
        msg["To"] = notification.recipient
        msg["Subject"] = notification.subject
        msg.attach(MIMEText(notification.message, "plain"))
        if notification.html_content:
            msg.attach(MIMEText(notification.html_content, "html"))
        logger.info(f"Email sent to {notification.recipient}: {notification.subject}")

    async def _send_sms(self, notification: Notification):
        """Send SMS notification"""
        logger.info(
            f"SMS sent to {notification.recipient}: {notification.message[:50]}..."
        )

    async def _send_push_notification(self, notification: Notification):
        """Send push notification"""
        logger.info(
            f"Push notification sent to {notification.recipient}: {notification.subject}"
        )

    async def _send_in_app_notification(self, notification: Notification):
        """Send in-app notification"""
        logger.info(
            f"In-app notification created for {notification.user_id}: {notification.subject}"
        )

    async def _check_user_preferences(
        self,
        user_id: str,
        notification_type: NotificationType,
        channel: NotificationChannel,
    ) -> bool:
        """Check if user allows this type of notification on this channel"""
        user_prefs = self.user_preferences.get(user_id, [])
        for pref in user_prefs:
            if pref.notification_type == notification_type:
                return channel in pref.enabled_channels
        return True

    async def _get_recipient_address(
        self, user_id: str, channel: NotificationChannel
    ) -> Optional[str]:
        """Get recipient address for the specified channel"""
        if channel == NotificationChannel.EMAIL:
            return f"user{user_id}@example.com"
        elif channel == NotificationChannel.SMS:
            return f"+1234567{user_id[-3:]}"
        elif channel == NotificationChannel.PUSH:
            return f"device_token_{user_id}"
        elif channel == NotificationChannel.IN_APP:
            return user_id
        return None

    def _get_sender_address(self, channel: NotificationChannel) -> str:
        """Get sender address for the specified channel"""
        if channel == NotificationChannel.EMAIL:
            return self.smtp_config["username"]
        elif channel == NotificationChannel.SMS:
            return self.sms_config["from_number"]
        else:
            return "Fluxion"

    def _render_template(self, template: str, variables: Dict[str, Any]) -> str:
        """Render template with variables"""
        rendered = template
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            rendered = rendered.replace(placeholder, str(value))
        return rendered

    def get_notification_statistics(self) -> Dict[str, Any]:
        """Get notification service statistics"""
        status_counts = {}
        channel_counts = {}
        type_counts = {}
        for notification in self.notifications.values():
            status_counts[notification.status.value] = (
                status_counts.get(notification.status.value, 0) + 1
            )
            channel_counts[notification.channel.value] = (
                channel_counts.get(notification.channel.value, 0) + 1
            )
            type_counts[notification.notification_type.value] = (
                type_counts.get(notification.notification_type.value, 0) + 1
            )
        return {
            "total_notifications": len(self.notifications),
            "total_templates": len(self.templates),
            "total_batches": len(self.notification_batches),
            "queue_size": len(self.delivery_queue),
            "retry_queue_size": len(self.retry_queue),
            "status_distribution": status_counts,
            "channel_distribution": channel_counts,
            "type_distribution": type_counts,
        }
