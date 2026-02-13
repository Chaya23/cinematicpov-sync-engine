#!/usr/bin/env python3
"""
Performance Monitoring Script for CinematicPOV Sync Engine
Monitors app performance metrics and health
"""

import psutil
import time
import json
from datetime import datetime
from typing import Dict

class PerformanceMonitor:
    """Monitor application performance metrics"""
    
    def __init__(self):
        self.metrics = {
            'timestamp': None,
            'cpu_percent': 0,
            'memory_mb': 0,
            'memory_percent': 0,
            'disk_usage_percent': 0,
            'network_io': {},
            'health_status': 'unknown'
        }
    
    def collect_system_metrics(self) -> Dict:
        """Collect current system metrics"""
        import os
        process = psutil.Process(os.getpid())
        
        self.metrics['timestamp'] = datetime.now().isoformat()
        self.metrics['cpu_percent'] = psutil.cpu_percent(interval=1)
        self.metrics['memory_mb'] = process.memory_info().rss / 1024 / 1024
        self.metrics['memory_percent'] = process.memory_percent()
        
        disk = psutil.disk_usage('/')
        self.metrics['disk_usage_percent'] = disk.percent
        
        # Network I/O
        net_io = psutil.net_io_counters()
        self.metrics['network_io'] = {
            'bytes_sent': net_io.bytes_sent,
            'bytes_recv': net_io.bytes_recv
        }
        
        return self.metrics
    
    def check_health(self) -> str:
        """Check overall health status"""
        issues = []
        
        if self.metrics['cpu_percent'] > 80:
            issues.append('High CPU usage')
        
        if self.metrics['memory_percent'] > 80:
            issues.append('High memory usage')
        
        if self.metrics['disk_usage_percent'] > 90:
            issues.append('Low disk space')
        
        if issues:
            self.metrics['health_status'] = 'warning'
            self.metrics['issues'] = issues
        else:
            self.metrics['health_status'] = 'healthy'
            self.metrics['issues'] = []
        
        return self.metrics['health_status']
    
    def generate_report(self) -> str:
        """Generate performance report"""
        self.collect_system_metrics()
        health = self.check_health()
        
        report = f"""
╔══════════════════════════════════════════════════════════╗
║  🎬 CinematicPOV Sync Engine - Performance Report        ║
╚══════════════════════════════════════════════════════════╝

⏰ Timestamp: {self.metrics['timestamp']}

📊 System Metrics:
   • CPU Usage:    {self.metrics['cpu_percent']:.1f}%
   • Memory:       {self.metrics['memory_mb']:.1f} MB ({self.metrics['memory_percent']:.1f}%)
   • Disk Usage:   {self.metrics['disk_usage_percent']:.1f}%

🌐 Network I/O:
   • Sent:         {self.metrics['network_io']['bytes_sent'] / 1024 / 1024:.2f} MB
   • Received:     {self.metrics['network_io']['bytes_recv'] / 1024 / 1024:.2f} MB

🏥 Health Status: {health.upper()}
"""
        
        if self.metrics.get('issues'):
            report += "\n⚠️  Issues Detected:\n"
            for issue in self.metrics['issues']:
                report += f"   • {issue}\n"
        
        report += "\n" + "═" * 60 + "\n"
        
        return report
    
    def save_metrics(self, filepath: str = 'performance_metrics.json'):
        """Save metrics to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(self.metrics, f, indent=2)


def main():
    """Main monitoring function"""
    monitor = PerformanceMonitor()
    
    print(monitor.generate_report())
    
    # Save metrics
    monitor.save_metrics()
    print("💾 Metrics saved to performance_metrics.json")
    
    # Return exit code based on health
    if monitor.metrics['health_status'] == 'healthy':
        return 0
    else:
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
