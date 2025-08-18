"""
Alerts and Notifications System
"""

import smtplib
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import logging
import sqlite3
from pathlib import Path

class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class AlertChannel(str, Enum):
    EMAIL = "email"
    SLACK = "slack"
    SMS = "sms"
    WEBHOOK = "webhook"
    DATABASE = "database"

@dataclass
class Alert:
    id: str
    title: str
    message: str
    severity: AlertSeverity
    category: str
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'severity': self.severity.value,
            'category': self.category,
            'timestamp': self.timestamp.isoformat(),
            'details': self.details,
            'resolved': self.resolved,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }

class AlertRule:
    """Base class for alert rules"""
    
    def __init__(self, name: str, severity: AlertSeverity, channels: List[AlertChannel]):
        self.name = name
        self.severity = severity
        self.channels = channels
        self.cooldown_minutes = 30  # Prevent spam
        self.last_triggered = None
    
    def should_trigger(self, data: Dict[str, Any]) -> bool:
        """Override in subclasses to define trigger conditions"""
        return False
    
    def can_trigger(self) -> bool:
        """Check if enough time has passed since last trigger"""
        if self.last_triggered is None:
            return True
        
        time_since_last = datetime.now() - self.last_triggered
        return time_since_last.total_seconds() > (self.cooldown_minutes * 60)
    
    def create_alert(self, data: Dict[str, Any]) -> Alert:
        """Create alert from rule and data"""
        alert_id = f"{self.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return Alert(
            id=alert_id,
            title=f"Alert: {self.name}",
            message=self.generate_message(data),
            severity=self.severity,
            category=self.name,
            timestamp=datetime.now(),
            details=data
        )
    
    def generate_message(self, data: Dict[str, Any]) -> str:
        """Generate alert message - override in subclasses"""
        return f"Alert triggered for {self.name}"

class FinancialThresholdAlert(AlertRule):
    """Alert for financial thresholds"""
    
    def __init__(self, threshold_amount: float, comparison: str = "greater", 
                 currency: str = "USD", **kwargs):
        super().__init__(**kwargs)
        self.threshold_amount = threshold_amount
        self.comparison = comparison  # greater, less, equal
        self.currency = currency
    
    def should_trigger(self, data: Dict[str, Any]) -> bool:
        amount = data.get('amount', 0)
        
        if self.comparison == "greater":
            return amount > self.threshold_amount
        elif self.comparison == "less":
            return amount < self.threshold_amount
        elif self.comparison == "equal":
            return abs(amount - self.threshold_amount) < 0.01
        
        return False
    
    def generate_message(self, data: Dict[str, Any]) -> str:
        amount = data.get('amount', 0)
        operation = data.get('operation', 'Unknown operation')
        
        return (f"Financial threshold exceeded: {operation} amount of "
                f"{self.currency} {amount:,.2f} is {self.comparison} than "
                f"threshold of {self.currency} {self.threshold_amount:,.2f}")

class AnomalyDetectionAlert(AlertRule):
    """Alert for detecting anomalies in financial data"""
    
    def __init__(self, metric: str, deviation_threshold: float = 2.0, **kwargs):
        super().__init__(**kwargs)
        self.metric = metric
        self.deviation_threshold = deviation_threshold
        self.historical_data = []
    
    def should_trigger(self, data: Dict[str, Any]) -> bool:
        current_value = data.get(self.metric, 0)
        
        if len(self.historical_data) < 10:  # Need baseline data
            self.historical_data.append(current_value)
            return False
        
        # Calculate mean and standard deviation
        mean = sum(self.historical_data) / len(self.historical_data)
        variance = sum((x - mean) ** 2 for x in self.historical_data) / len(self.historical_data)
        std_dev = variance ** 0.5
        
        # Check if current value is an anomaly
        if std_dev > 0:
            z_score = abs(current_value - mean) / std_dev
            is_anomaly = z_score > self.deviation_threshold
            
            # Update historical data (rolling window)
            self.historical_data.append(current_value)
            if len(self.historical_data) > 100:
                self.historical_data.pop(0)
            
            return is_anomaly
        
        return False
    
    def generate_message(self, data: Dict[str, Any]) -> str:
        current_value = data.get(self.metric, 0)
        return (f"Anomaly detected in {self.metric}: current value {current_value} "
                f"deviates significantly from historical pattern")

class SystemHealthAlert(AlertRule):
    """Alert for system health issues"""
    
    def __init__(self, health_check: str, **kwargs):
        super().__init__(**kwargs)
        self.health_check = health_check
    
    def should_trigger(self, data: Dict[str, Any]) -> bool:
        health_status = data.get('health_status', 'unknown')
        return health_status in ['warning', 'critical']
    
    def generate_message(self, data: Dict[str, Any]) -> str:
        health_status = data.get('health_status', 'unknown')
        health_message = data.get('health_message', 'No details available')
        
        return f"System health issue in {self.health_check}: {health_status.upper()} - {health_message}"

class NotificationChannel:
    """Base class for notification channels"""
    
    def send(self, alert: Alert) -> bool:
        """Send alert through this channel"""
        raise NotImplementedError

class EmailNotificationChannel(NotificationChannel):
    """Email notification channel"""
    
    def __init__(self, smtp_server: str, smtp_port: int, username: str, 
                 password: str, from_email: str, to_emails: List[str]):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.to_emails = to_emails
    
    def send(self, alert: Alert) -> bool:
        try:
            msg = MimeMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            msg['Subject'] = f"[{alert.severity.upper()}] {alert.title}"
            
            # Create email body
            body = f"""
            Alert Details:
            
            Title: {alert.title}
            Severity: {alert.severity.upper()}
            Category: {alert.category}
            Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
            
            Message:
            {alert.message}
            
            Additional Details:
            {json.dumps(alert.details, indent=2) if alert.details else 'None'}
            """
            
            msg.attach(MimeText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to send email alert: {str(e)}")
            return False

class SlackNotificationChannel(NotificationChannel):
    """Slack notification channel"""
    
    def __init__(self, webhook_url: str, channel: str = None):
        self.webhook_url = webhook_url
        self.channel = channel
    
    def send(self, alert: Alert) -> bool:
        try:
            # Color based on severity
            color_map = {
                AlertSeverity.INFO: "#36a64f",
                AlertSeverity.WARNING: "#ff9500",
                AlertSeverity.CRITICAL: "#ff0000",
                AlertSeverity.EMERGENCY: "#8B0000"
            }
            
            payload = {
                "text": f"Cash Flow Dashboard Alert: {alert.title}",
                "attachments": [
                    {
                        "color": color_map.get(alert.severity, "#36a64f"),
                        "fields": [
                            {
                                "title": "Severity",
                                "value": alert.severity.upper(),
                                "short": True
                            },
                            {
                                "title": "Category",
                                "value": alert.category,
                                "short": True
                            },
                            {
                                "title": "Time",
                                "value": alert.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                                "short": True
                            },
                            {
                                "title": "Message",
                                "value": alert.message,
                                "short": False
                            }
                        ]
                    }
                ]
            }
            
            if self.channel:
                payload["channel"] = self.channel
            
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            logging.error(f"Failed to send Slack alert: {str(e)}")
            return False

class DatabaseNotificationChannel(NotificationChannel):
    """Database storage for alerts"""
    
    def __init__(self, db_path: str = "alerts.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize alerts database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                severity TEXT NOT NULL,
                category TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                details TEXT,
                resolved BOOLEAN DEFAULT FALSE,
                resolved_at TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def send(self, alert: Alert) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO alerts (id, title, message, severity, category, timestamp, details, resolved, resolved_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                alert.id,
                alert.title,
                alert.message,
                alert.severity.value,
                alert.category,
                alert.timestamp.isoformat(),
                json.dumps(alert.details) if alert.details else None,
                alert.resolved,
                alert.resolved_at.isoformat() if alert.resolved_at else None
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logging.error(f"Failed to store alert in database: {str(e)}")
            return False

class AlertManager:
    """Main alert management system"""
    
    def __init__(self):
        self.rules: List[AlertRule] = []
        self.channels: Dict[AlertChannel, NotificationChannel] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.logger = logging.getLogger(__name__)
    
    def add_rule(self, rule: AlertRule):
        """Add an alert rule"""
        self.rules.append(rule)
    
    def add_channel(self, channel_type: AlertChannel, channel: NotificationChannel):
        """Add a notification channel"""
        self.channels[channel_type] = channel
    
    def check_rules(self, data: Dict[str, Any], context: str = "general"):
        """Check all rules against provided data"""
        triggered_alerts = []
        
        for rule in self.rules:
            if rule.should_trigger(data) and rule.can_trigger():
                alert = rule.create_alert(data)
                self.active_alerts[alert.id] = alert
                
                # Send through configured channels
                for channel_type in rule.channels:
                    if channel_type in self.channels:
                        success = self.channels[channel_type].send(alert)
                        if success:
                            self.logger.info(f"Alert {alert.id} sent via {channel_type.value}")
                        else:
                            self.logger.error(f"Failed to send alert {alert.id} via {channel_type.value}")
                
                rule.last_triggered = datetime.now()
                triggered_alerts.append(alert)
        
        return triggered_alerts
    
    def resolve_alert(self, alert_id: str):
        """Mark an alert as resolved"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].resolved = True
            self.active_alerts[alert_id].resolved_at = datetime.now()
    
    def get_active_alerts(self, severity: AlertSeverity = None) -> List[Alert]:
        """Get active (unresolved) alerts"""
        alerts = [alert for alert in self.active_alerts.values() if not alert.resolved]
        
        if severity:
            alerts = [alert for alert in alerts if alert.severity == severity]
        
        return sorted(alerts, key=lambda x: x.timestamp, reverse=True)
    
    def setup_default_rules(self, config: Dict[str, Any]):
        """Setup default alert rules"""
        # High cost transaction alert
        self.add_rule(FinancialThresholdAlert(
            name="high_cost_transaction",
            threshold_amount=config.get('high_cost_threshold', 10000),
            comparison="greater",
            severity=AlertSeverity.WARNING,
            channels=[AlertChannel.EMAIL, AlertChannel.DATABASE]
        ))
        
        # Low cash flow alert
        self.add_rule(FinancialThresholdAlert(
            name="low_cash_flow",
            threshold_amount=config.get('low_cash_threshold', 1000),
            comparison="less",
            severity=AlertSeverity.CRITICAL,
            channels=[AlertChannel.EMAIL, AlertChannel.SLACK, AlertChannel.DATABASE]
        ))
        
        # Anomaly detection for daily costs
        self.add_rule(AnomalyDetectionAlert(
            name="daily_cost_anomaly",
            metric="daily_total_cost",
            deviation_threshold=2.5,
            severity=AlertSeverity.WARNING,
            channels=[AlertChannel.DATABASE]
        ))
        
        # System health alerts
        self.add_rule(SystemHealthAlert(
            name="database_health",
            health_check="database",
            severity=AlertSeverity.CRITICAL,
            channels=[AlertChannel.EMAIL, AlertChannel.DATABASE]
        ))

# Global alert manager instance
alert_manager = AlertManager()

def setup_alerts(config: Dict[str, Any]):
    """Setup alert system with configuration"""
    # Setup notification channels
    if config.get('email_enabled'):
        email_channel = EmailNotificationChannel(
            smtp_server=config['smtp_server'],
            smtp_port=config['smtp_port'],
            username=config['smtp_username'],
            password=config['smtp_password'],
            from_email=config['from_email'],
            to_emails=config['alert_emails']
        )
        alert_manager.add_channel(AlertChannel.EMAIL, email_channel)
    
    if config.get('slack_webhook_url'):
        slack_channel = SlackNotificationChannel(
            webhook_url=config['slack_webhook_url'],
            channel=config.get('slack_channel')
        )
        alert_manager.add_channel(AlertChannel.SLACK, slack_channel)
    
    # Always setup database channel
    db_channel = DatabaseNotificationChannel()
    alert_manager.add_channel(AlertChannel.DATABASE, db_channel)
    
    # Setup default rules
    alert_manager.setup_default_rules(config)

def trigger_financial_alert(operation: str, amount: float, currency: str = "USD", details: Dict[str, Any] = None):
    """Trigger financial threshold checks"""
    data = {
        'operation': operation,
        'amount': amount,
        'currency': currency,
        'timestamp': datetime.now().isoformat(),
        **(details or {})
    }
    
    return alert_manager.check_rules(data, context="financial")

def trigger_health_alert(check_name: str, status: str, message: str, details: Dict[str, Any] = None):
    """Trigger system health alerts"""
    data = {
        'health_check': check_name,
        'health_status': status,
        'health_message': message,
        'timestamp': datetime.now().isoformat(),
        **(details or {})
    }
    
    return alert_manager.check_rules(data, context="health")

def get_alert_dashboard_data() -> Dict[str, Any]:
    """Get data for alert dashboard"""
    active_alerts = alert_manager.get_active_alerts()
    
    return {
        'total_active': len(active_alerts),
        'critical_count': len([a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]),
        'warning_count': len([a for a in active_alerts if a.severity == AlertSeverity.WARNING]),
        'recent_alerts': active_alerts[:10],
        'alert_categories': list(set(a.category for a in active_alerts))
    }
