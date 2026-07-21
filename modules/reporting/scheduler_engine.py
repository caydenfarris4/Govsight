"""
Report Scheduler Engine
Phase 3: Automated report generation with cron-based scheduling

ARCHITECTURAL DECISIONS:
1. Uses APScheduler for robust scheduling
2. SQLite database for schedule persistence
3. Background thread for non-blocking execution
4. Timezone-aware scheduling
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
import threading
import queue

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False
    print("APScheduler not available. Install with: pip install apscheduler")

from modules.reporting.report_engine import ReportEngine
from modules.reporting.google_drive_connector import get_google_drive_connector
from modules.reporting.audit_logger import ReportAuditLogger

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SchedulerEngine:
    """Engine for scheduling and executing automated reports"""
    
    def __init__(self):
        self.scheduler = None
        self.schedules_db = "databases/report_schedules.db"
        self.job_queue = queue.Queue()
        self.worker_thread = None
        self.report_engine = ReportEngine()
        self.audit_logger = ReportAuditLogger()
        self.gdrive_connector = None
        
        # Ensure database exists
        os.makedirs("databases", exist_ok=True)
        self.init_database()
        self.init_scheduler()
    
    def init_database(self):
        """Initialize the schedules database"""
        conn = sqlite3.connect(self.schedules_db)
        cursor = conn.cursor()
        
        # Schedules table already created in admin panel
        # Just ensure execution history table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schedule_execution (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                schedule_id INTEGER,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                status TEXT,
                report_path TEXT,
                google_drive_link TEXT,
                error_message TEXT,
                recipients_notified TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (schedule_id) REFERENCES report_schedules(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def init_scheduler(self):
        """Initialize the APScheduler"""
        if not SCHEDULER_AVAILABLE:
            logger.error("APScheduler not available")
            return False
        
        try:
            # Configure job stores
            jobstores = {
                'default': SQLAlchemyJobStore(url=f'sqlite:///{self.schedules_db}')
            }
            
            # Configure job defaults
            job_defaults = {
                'coalesce': True,
                'max_instances': 3,
                'misfire_grace_time': 3600  # 1 hour grace time
            }
            
            # Create scheduler
            self.scheduler = BackgroundScheduler(
                jobstores=jobstores,
                job_defaults=job_defaults,
                timezone='US/Eastern'
            )
            
            # Start scheduler
            self.scheduler.start()
            
            # Start worker thread
            self.worker_thread = threading.Thread(target=self._worker, daemon=True)
            self.worker_thread.start()
            
            # Initialize Google Drive connector
            try:
                from modules.reporting.google_drive_connector import get_google_drive_connector
                self.gdrive_connector = get_google_drive_connector()
            except:
                logger.warning("Google Drive connector not available")
            
            logger.info("Scheduler engine initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize scheduler: {e}")
            return False
    
    def _worker(self):
        """Worker thread to process scheduled jobs"""
        while True:
            try:
                job = self.job_queue.get(timeout=60)
                if job is None:
                    break
                
                self._execute_report(job)
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker error: {e}")
    
    def add_schedule(self, schedule_config: Dict) -> str:
        """
        Add a new report schedule
        
        Args:
            schedule_config: Configuration dictionary with:
                - module: Module name (vatica, navi, mantis)
                - report_name: Name of the report
                - report_type: Type of report
                - frequency: Daily, Weekly, Monthly, Quarterly
                - schedule_time: Time in HH:MM format
                - day_of_week: For weekly (0=Monday, 6=Sunday)
                - day_of_month: For monthly (1-28)
                - distribution_channels: List of channels
                - recipients: List of email addresses
                - google_drive_folder: Target folder in Drive
        
        Returns:
            Schedule ID
        """
        conn = sqlite3.connect(self.schedules_db)
        cursor = conn.cursor()
        
        try:
            # Insert schedule into database
            cursor.execute("""
                INSERT INTO report_schedules 
                (module, report_name, report_type, frequency, schedule_time, 
                 day_of_week, day_of_month, distribution_channels, recipients, 
                 google_drive_folder, enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                schedule_config['module'],
                schedule_config['report_name'],
                schedule_config['report_type'],
                schedule_config['frequency'],
                schedule_config.get('schedule_time'),
                schedule_config.get('day_of_week'),
                schedule_config.get('day_of_month'),
                json.dumps(schedule_config.get('distribution_channels', [])),
                json.dumps(schedule_config.get('recipients', [])),
                schedule_config.get('google_drive_folder', 'GovSight Reports')
            ))
            
            schedule_id = cursor.lastrowid
            conn.commit()
            
            # Add to APScheduler if available
            if self.scheduler:
                self._add_job_to_scheduler(schedule_id, schedule_config)
            
            logger.info(f"Added schedule {schedule_id}: {schedule_config['report_name']}")
            return str(schedule_id)
            
        except Exception as e:
            logger.error(f"Error adding schedule: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _add_job_to_scheduler(self, schedule_id: int, config: Dict):
        """Add a job to the APScheduler"""
        if not self.scheduler:
            return
        
        try:
            frequency = config['frequency']
            schedule_time = config.get('schedule_time', '08:00')
            hour, minute = map(int, schedule_time.split(':'))
            
            # Create trigger based on frequency
            if frequency == 'Daily':
                trigger = CronTrigger(hour=hour, minute=minute)
                
            elif frequency == 'Weekly':
                day_of_week = config.get('day_of_week', 'Monday')
                day_map = {
                    'Monday': 0, 'Tuesday': 1, 'Wednesday': 2,
                    'Thursday': 3, 'Friday': 4, 'Saturday': 5, 'Sunday': 6
                }
                trigger = CronTrigger(
                    day_of_week=day_map.get(day_of_week, 0),
                    hour=hour,
                    minute=minute
                )
                
            elif frequency == 'Monthly':
                day = config.get('day_of_month', 1)
                trigger = CronTrigger(day=day, hour=hour, minute=minute)
                
            elif frequency == 'Quarterly':
                # Run on 1st day of Jan, Apr, Jul, Oct
                trigger = CronTrigger(month='1,4,7,10', day=1, hour=hour, minute=minute)
                
            else:
                logger.warning(f"Unknown frequency: {frequency}")
                return
            
            # Add job
            self.scheduler.add_job(
                func=self._schedule_job_handler,
                trigger=trigger,
                args=[schedule_id],
                id=f"schedule_{schedule_id}",
                name=f"{config['module']}_{config['report_name']}",
                replace_existing=True
            )
            
            logger.info(f"Added job to scheduler: schedule_{schedule_id}")
            
        except Exception as e:
            logger.error(f"Error adding job to scheduler: {e}")
    
    def _schedule_job_handler(self, schedule_id: int):
        """Handler called by scheduler to queue a job"""
        self.job_queue.put({
            'schedule_id': schedule_id,
            'timestamp': datetime.now()
        })
    
    def _execute_report(self, job: Dict):
        """Execute a scheduled report"""
        schedule_id = job['schedule_id']
        
        # Get schedule details
        conn = sqlite3.connect(self.schedules_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT module, report_name, report_type, distribution_channels, 
                   recipients, google_drive_folder
            FROM report_schedules
            WHERE id = ?
        """, (schedule_id,))
        
        schedule = cursor.fetchone()
        if not schedule:
            logger.error(f"Schedule {schedule_id} not found")
            return
        
        module, report_name, report_type, channels_json, recipients_json, gdrive_folder = schedule
        channels = json.loads(channels_json) if channels_json else []
        recipients = json.loads(recipients_json) if recipients_json else []
        
        # Record execution start
        cursor.execute("""
            INSERT INTO schedule_execution (schedule_id, start_time, status)
            VALUES (?, ?, 'running')
        """, (schedule_id, datetime.now()))
        
        execution_id = cursor.lastrowid
        conn.commit()
        
        try:
            # Generate the report
            report_path = self._generate_report(module, report_name, report_type)
            
            # Distribute the report
            distribution_results = self._distribute_report(
                report_path, channels, recipients, gdrive_folder
            )
            
            # Update execution record
            cursor.execute("""
                UPDATE schedule_execution
                SET end_time = ?, status = 'completed', report_path = ?, 
                    google_drive_link = ?, recipients_notified = ?
                WHERE id = ?
            """, (
                datetime.now(),
                report_path,
                distribution_results.get('google_drive_link'),
                json.dumps(distribution_results.get('recipients_notified', [])),
                execution_id
            ))
            
            # Update last_run and calculate next_run
            cursor.execute("""
                UPDATE report_schedules
                SET last_run = ?
                WHERE id = ?
            """, (datetime.now(), schedule_id))
            
            conn.commit()
            logger.info(f"Successfully executed schedule {schedule_id}")
            
        except Exception as e:
            logger.error(f"Error executing schedule {schedule_id}: {e}")
            
            # Update execution record with error
            cursor.execute("""
                UPDATE schedule_execution
                SET end_time = ?, status = 'failed', error_message = ?
                WHERE id = ?
            """, (datetime.now(), str(e), execution_id))
            
            conn.commit()
        
        finally:
            conn.close()
    
    def _generate_report(self, module: str, report_name: str, report_type: str) -> str:
        """Generate a report and return the file path"""
        # This is a simplified version - in production, would call actual report generators
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{module}_{report_name.replace(' ', '_')}_{timestamp}.pdf"
        filepath = f"/tmp/{filename}"
        
        # Generate report based on module and type
        try:
            if module == "vatica":
                from modules.vatica.reports_integration import vatica_reports
                # Generate appropriate Vatica report
                content = f"Vatica {report_name} Report\nGenerated: {datetime.now()}"
                
            elif module == "navi":
                from modules.navi.reports_integration import navi_reports
                # Generate appropriate Navi report
                content = f"Navi {report_name} Report\nGenerated: {datetime.now()}"
                
            elif module == "mantis":
                from modules.mantis.reports_integration import mantis_reports
                # Generate appropriate Mantis report
                content = f"Mantis {report_name} Report\nGenerated: {datetime.now()}"
            
            else:
                content = f"{module} {report_name} Report\nGenerated: {datetime.now()}"
            
            # For now, create a simple text file
            with open(filepath, 'w') as f:
                f.write(content)
            
            return filepath
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            raise
    
    def _distribute_report(self, 
                          report_path: str,
                          channels: List[str],
                          recipients: List[str],
                          gdrive_folder: str) -> Dict:
        """Distribute report through specified channels"""
        results = {}
        
        # Google Drive distribution
        if 'google_drive' in channels and self.gdrive_connector:
            try:
                upload_result = self.gdrive_connector.upload_file(
                    report_path,
                    folder_name=gdrive_folder,
                    custom_name=os.path.basename(report_path)
                )
                
                if upload_result.get('status') == 'success':
                    results['google_drive_link'] = upload_result.get('webLink')
                    logger.info(f"Uploaded to Google Drive: {upload_result.get('fileId')}")
                    
            except Exception as e:
                logger.error(f"Google Drive upload failed: {e}")
        
        # Email distribution (placeholder)
        if 'email' in channels and recipients:
            # In production, would send actual emails
            results['recipients_notified'] = recipients
            logger.info(f"Would email to: {recipients}")
        
        return results
    
    def get_schedule_status(self, schedule_id: int) -> Dict:
        """Get status of a schedule"""
        conn = sqlite3.connect(self.schedules_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM report_schedules WHERE id = ?
        """, (schedule_id,))
        
        schedule = cursor.fetchone()
        
        # Get recent executions
        cursor.execute("""
            SELECT * FROM schedule_execution 
            WHERE schedule_id = ?
            ORDER BY created_at DESC
            LIMIT 5
        """, (schedule_id,))
        
        executions = cursor.fetchall()
        
        conn.close()
        
        return {
            'schedule': schedule,
            'recent_executions': executions
        }
    
    def pause_schedule(self, schedule_id: int):
        """Pause a schedule"""
        if self.scheduler:
            try:
                self.scheduler.pause_job(f"schedule_{schedule_id}")
            except:
                pass
        
        conn = sqlite3.connect(self.schedules_db)
        cursor = conn.cursor()
        cursor.execute("UPDATE report_schedules SET enabled = 0 WHERE id = ?", (schedule_id,))
        conn.commit()
        conn.close()
    
    def resume_schedule(self, schedule_id: int):
        """Resume a schedule"""
        if self.scheduler:
            try:
                self.scheduler.resume_job(f"schedule_{schedule_id}")
            except:
                pass
        
        conn = sqlite3.connect(self.schedules_db)
        cursor = conn.cursor()
        cursor.execute("UPDATE report_schedules SET enabled = 1 WHERE id = ?", (schedule_id,))
        conn.commit()
        conn.close()
    
    def delete_schedule(self, schedule_id: int):
        """Delete a schedule"""
        if self.scheduler:
            try:
                self.scheduler.remove_job(f"schedule_{schedule_id}")
            except:
                pass
        
        conn = sqlite3.connect(self.schedules_db)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM report_schedules WHERE id = ?", (schedule_id,))
        conn.commit()
        conn.close()
    
    def shutdown(self):
        """Shutdown the scheduler"""
        if self.scheduler:
            self.scheduler.shutdown()
        
        # Stop worker thread
        self.job_queue.put(None)
        if self.worker_thread:
            self.worker_thread.join(timeout=5)


# Singleton instance
_scheduler_engine = None

def get_scheduler_engine() -> SchedulerEngine:
    """Get or create the scheduler engine instance"""
    global _scheduler_engine
    if _scheduler_engine is None:
        _scheduler_engine = SchedulerEngine()
    return _scheduler_engine