"""
NexusVault Sovereign Database Adapter (src/nexus_db_adapter.py)
Manages persistence, support tickets, tenant metadata, RLS boundaries, and AI Auto-Responses.
"""

import sqlite3
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.developer_kb import NEXUSVAULT_EXECUTIVE_KB

DB_PATH = "nexus_sovereign.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nv_tenants (
            tenant_id TEXT PRIMARY KEY,
            org_name TEXT NOT NULL,
            admin_email TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING_ACTIVATION',
            is_activated INTEGER DEFAULT 0,
            demo_days_assigned INTEGER DEFAULT 14,
            demo_expires_at TIMESTAMP,
            desk_operator TEXT DEFAULT 'Authorized Desk Officer',
            solicited_vendor_status TEXT DEFAULT 'Managed via Internal Admin Settings',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nv_support_tickets (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            tenant_slug TEXT NOT NULL,
            org_name TEXT NOT NULL,
            sender_email TEXT NOT NULL,
            message TEXT NOT NULL,
            response TEXT,
            status TEXT DEFAULT 'OPEN',
            is_auto_responded INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            responded_at TIMESTAMP,
            FOREIGN KEY (tenant_id) REFERENCES nv_tenants(tenant_id)
        )
    ''')
    
    conn.commit()
    conn.close()

def match_knowledge_base(message: str) -> Optional[str]:
    """Matches user query against src/developer_kb.py for automated responses."""
    msg_lower = message.lower()
    
    for topic, topic_data in NEXUSVAULT_EXECUTIVE_KB.items():
        for qa in topic_data["qa_pairs"]:
            q_text = qa["question"].lower()
            # Simple keyword matching logic
            keywords = [w for w in q_text.split() if len(w) > 3]
            match_count = sum(1 for kw in keywords if kw in msg_lower)
            
            if match_count >= 2 or topic.lower() in msg_lower:
                return f"**[AUTOMATED SYSTEM INTELLIGENCE BRIEFING]**\n\n{qa['answer']}\n\n*Note: This response was generated automatically from the NexusVault Knowledge Base. If further escalation is required, the Lead Architect has been notified.*"
                
    return None

def create_support_ticket(tenant_id: str, tenant_slug: str, org_name: str, sender_email: str, message: str) -> bool:
    """Inserts inquiry and executes instant AI auto-response if match exists."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        auto_answer = match_knowledge_base(message)
        
        if auto_answer:
            status = 'RESOLVED (AI AUTO-REPLY)'
            response = auto_answer
            is_auto = 1
            resp_time = datetime.now().isoformat()
        else:
            status = 'OPEN'
            response = None
            is_auto = 0
            resp_time = None
            
        cursor.execute('''
            INSERT INTO nv_support_tickets (tenant_id, tenant_slug, org_name, sender_email, message, response, status, is_auto_responded, created_at, responded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
        ''', (tenant_id, tenant_slug, org_name, sender_email, message, response, status, is_auto, resp_time))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating support ticket: {e}")
        return False

def get_all_support_tickets() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ticket_id, tenant_id, tenant_slug, org_name, sender_email, message, response, status, is_auto_responded, created_at, responded_at
        FROM nv_support_tickets
        ORDER BY created_at DESC
    ''')
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_tenant_support_tickets(tenant_slug: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ticket_id, sender_email, message, response, status, is_auto_responded, created_at, responded_at
        FROM nv_support_tickets
        WHERE tenant_slug = ?
        ORDER BY created_at DESC
    ''', (tenant_slug,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def respond_to_support_ticket(ticket_id: int, response_text: str) -> bool:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE nv_support_tickets
            SET response = ?, status = 'RESOLVED (CEO RESPONSE)', responded_at = ?
            WHERE ticket_id = ?
        ''', (response_text, datetime.now().isoformat(), ticket_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error responding to ticket: {e}")
        return False

init_db()
