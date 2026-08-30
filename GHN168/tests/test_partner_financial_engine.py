#!/usr/bin/env python3
"""
================================================================================
GHN168 Partner Financial Engine (3-Pillar) Comprehensive Test Suite
================================================================================
Tests the 3 dimensions of Partner Financial Management:
1. Pillar 1: Lead Hunter Dimension (Gross Volume, Net Internal, Peer-Sharing, Leaderboard)
2. Pillar 2: Labor Earned Dimension (Actual Cumulative Wages/Labor Earned YTD for Keng, Hom, Nick, Mod)
3. Pillar 3: Personal Vault & Central Pool Dimension (Partner Balances & Retained Earnings)
4. Chat Intent Detection & Flex Message Builders
5. REST API Endpoints (/api/partners/...)
================================================================================
"""

import os
import sys
from pathlib import Path

# Ensure workspace root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest
from fastapi.testclient import TestClient

from ghn168_sync_service import get_partner_financial_breakdown
from line_bot_server import (
    app,
    is_partner_financial_request,
    build_partner_hunter_flex_message,
    build_partner_labor_flex_message,
    build_partner_vault_flex_message,
    build_partner_all_in_one_financial_flex_message
)

from unittest.mock import MagicMock, patch

client = TestClient(app)


class TestPartnerFinancialEngine(unittest.TestCase):
    """Unit and Integration tests for the 3-Pillar Partner Financial Engine."""

    def setUp(self):
        # Patch requests.post to ensure 100% Zero Production Pollution
        self.patcher = patch("requests.post")
        self.mock_post = self.patcher.start()

        def mock_requests_post_handler(url, json=None, **kwargs):
            mock_res = MagicMock()
            mock_res.status_code = 200
            payload = json or {}
            req_type = payload.get("type", "")

            if req_type == "read":
                sheet_name = payload.get("sheetName")
                from ghn168_sync_service import get_simulated_sheet_data
                mock_data = get_simulated_sheet_data(sheet_name)
                mock_res.json.return_value = {
                    "status": "success",
                    "values": mock_data.get("values", [])
                }
            elif req_type in ["sync", "overwrite"]:
                mock_res.json.return_value = {
                    "status": "success",
                    "message": f"Mocked safe {req_type} to Google Sheets"
                }
            else:
                mock_res.json.return_value = {"status": "success", "message": "Mocked generic response"}

            return mock_res

        self.mock_post.side_effect = mock_requests_post_handler
        self.breakdown = get_partner_financial_breakdown()

    def tearDown(self):
        self.patcher.stop()

    def test_breakdown_status_and_structure(self):
        """Test overall structure of 3-pillar breakdown response."""
        self.assertEqual(self.breakdown["status"], "success")
        self.assertIn("pillar_1_lead_hunters", self.breakdown)
        self.assertIn("pillar_2_labor_earned", self.breakdown)
        self.assertIn("pillar_3_personal_vault", self.breakdown)

    def test_pillar_1_lead_hunter(self):
        """Test Pillar 1: Lead Hunter leaderboard & peer-sharing."""
        p1 = self.breakdown["pillar_1_lead_hunters"]
        leaderboard = p1.get("leaderboard", [])
        self.assertEqual(len(leaderboard), 4, "Must contain all 4 partners (Keng, Hom, Nick, Mod)")
        
        # Verify partners exist
        names = [p["short_name"] for p in leaderboard]
        self.assertIn("เก่ง", names)
        self.assertIn("หอม", names)
        self.assertIn("นิค", names)
        self.assertIn("มด", names)

        # Verify Leaderboard ordering (rank 1 must have highest gross)
        self.assertEqual(leaderboard[0]["rank"], 1)
        self.assertGreaterEqual(leaderboard[0]["hunter_gross"], leaderboard[1]["hunter_gross"])

        # Verify totals
        self.assertGreater(p1["total_gross_volume"], 0)
        self.assertGreater(p1["total_net_internal_volume"], 0)

    def test_pillar_2_labor_earned(self):
        """Test Pillar 2: Labor Earned YTD for partners."""
        p2 = self.breakdown["pillar_2_labor_earned"]
        partners = p2.get("partners", [])
        self.assertEqual(len(partners), 4)

        for p in partners:
            self.assertGreater(p["labor_ytd"], 0, f"Partner {p['short_name']} should have cumulative YTD labor")
            self.assertIn("labor_month", p)
            self.assertIn("projects_done", p)

        self.assertGreater(p2["total_labor_ytd"], 0)

    def test_pillar_3_personal_vault(self):
        """Test Pillar 3: Personal Vault and Corporate Central Pool."""
        p3 = self.breakdown["pillar_3_personal_vault"]
        self.assertEqual(p3["corporate_central_pool"], 450000.0)
        self.assertGreater(p3["total_partner_vaults"], 0)
        self.assertGreater(p3["grand_total_reserves"], 450000.0)

        partners = p3.get("partners", [])
        for p in partners:
            self.assertGreater(p["personal_vault_balance"], 0)

    def test_intent_detection_partner_financial(self):
        """Test chat intent recognition for all 3 pillars."""
        # Hunter intent
        t1, m1 = is_partner_financial_request("สรุปคนหางาน")
        self.assertTrue(t1)
        self.assertEqual(m1, "hunter")

        t1b, m1b = is_partner_financial_request("ผลงานหางาน")
        self.assertTrue(t1b)
        self.assertEqual(m1b, "hunter")

        # Labor intent
        t2, m2 = is_partner_financial_request("สรุปค่าแรงสะสม")
        self.assertTrue(t2)
        self.assertEqual(m2, "labor")

        t2b, m2b = is_partner_financial_request("ค่าแรง YTD")
        self.assertTrue(t2b)
        self.assertEqual(m2b, "labor")

        # Vault intent
        t3, m3 = is_partner_financial_request("ยอดเงินสะสมส่วนตัว")
        self.assertTrue(t3)
        self.assertEqual(m3, "vault")

        t3b, m3b = is_partner_financial_request("กองกลาง")
        self.assertTrue(t3b)
        self.assertEqual(m3b, "vault")

        # All-in-one intent
        t4, m4 = is_partner_financial_request("สรุปการเงินหุ้นส่วน")
        self.assertTrue(t4)
        self.assertEqual(m4, "all")

    def test_flex_message_builders(self):
        """Test all 4 Partner Financial Flex Message Cards."""
        card_hunter = build_partner_hunter_flex_message(self.breakdown)
        self.assertEqual(card_hunter["type"], "flex")
        self.assertEqual(card_hunter["contents"]["header"]["backgroundColor"], "#d97706")

        card_labor = build_partner_labor_flex_message(self.breakdown)
        self.assertEqual(card_labor["type"], "flex")
        self.assertEqual(card_labor["contents"]["header"]["backgroundColor"], "#2563eb")

        card_vault = build_partner_vault_flex_message(self.breakdown)
        self.assertEqual(card_vault["type"], "flex")
        self.assertEqual(card_vault["contents"]["header"]["backgroundColor"], "#7c3aed")

        card_all = build_partner_all_in_one_financial_flex_message(self.breakdown)
        self.assertEqual(card_all["type"], "flex")

    def test_api_partner_endpoints(self):
        """Test all REST API endpoints for Partner Financial Engine."""
        # Full breakdown
        r_all = client.get("/api/partners/financial_breakdown")
        self.assertEqual(r_all.status_code, 200)
        self.assertEqual(r_all.json()["status"], "success")

        # Hunter
        r_h = client.get("/api/partners/hunter")
        self.assertEqual(r_h.status_code, 200)
        self.assertIn("pillar_1_lead_hunters", r_h.json())

        # Labor
        r_l = client.get("/api/partners/labor")
        self.assertEqual(r_l.status_code, 200)
        self.assertIn("pillar_2_labor_earned", r_l.json())

        # Vault
        r_v = client.get("/api/partners/vault")
        self.assertEqual(r_v.status_code, 200)
        self.assertIn("pillar_3_personal_vault", r_v.json())


if __name__ == "__main__":
    unittest.main()
