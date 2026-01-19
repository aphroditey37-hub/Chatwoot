#!/usr/bin/env python3
"""
Backend API Testing for Financial Gaming Platform - Referral Tiers & Promotions Testing
Tests new referral tier system and promotions banner features
"""

import requests
import sys
import json
from datetime import datetime, timezone, timedelta

class FinancialPlatformTester:
    def __init__(self, base_url="https://gamepay-nexus.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api/v1"
        self.token = None
        self.admin_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.critical_issues = []

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, is_critical=False):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=10)

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"✅ PASSED - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict) and len(str(response_data)) < 300:
                        print(f"   Response: {response_data}")
                except:
                    pass
            else:
                print(f"❌ FAILED - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Raw response: {response.text[:200]}")
                
                failure_info = {
                    'name': name,
                    'expected': expected_status,
                    'actual': response.status_code,
                    'url': url,
                    'is_critical': is_critical
                }
                self.failed_tests.append(failure_info)
                
                if is_critical:
                    self.critical_issues.append(failure_info)

            return success, response.json() if response.content else {}

        except requests.exceptions.ConnectionError:
            print(f"❌ FAILED - Connection refused (server not running?)")
            failure_info = {'name': name, 'error': 'Connection refused', 'is_critical': is_critical}
            self.failed_tests.append(failure_info)
            if is_critical:
                self.critical_issues.append(failure_info)
            return False, {}
        except requests.exceptions.Timeout:
            print(f"❌ FAILED - Request timeout")
            failure_info = {'name': name, 'error': 'Timeout', 'is_critical': is_critical}
            self.failed_tests.append(failure_info)
            if is_critical:
                self.critical_issues.append(failure_info)
            return False, {}
        except Exception as e:
            print(f"❌ FAILED - Error: {str(e)}")
            failure_info = {'name': name, 'error': str(e), 'is_critical': is_critical}
            self.failed_tests.append(failure_info)
            if is_critical:
                self.critical_issues.append(failure_info)
            return False, {}

    def test_health_check(self):
        """Test basic health endpoint"""
        return self.run_test("Health Check", "GET", "health", 200, is_critical=True)

    def test_user_login(self):
        """Test regular user authentication"""
        success, response = self.run_test(
            "User Login (testuser/Test123456)",
            "POST",
            "auth/login",
            200,
            data={"username": "testuser", "password": "Test123456"},
            is_critical=True  # Critical for frontend testing
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            print(f"   🔑 User token obtained: {self.token[:20]}...")
            return True
        elif success and 'token' in response:
            self.token = response['token']
            print(f"   🔑 User token obtained: {self.token[:20]}...")
            return True
        
        return False

    def test_admin_login(self):
        """Test admin authentication"""
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data={"username": "admin", "password": "Admin123456"},
            is_critical=True  # Critical for admin features testing
        )
        
        if success and 'access_token' in response:
            # Store admin token separately
            self.admin_token = response['access_token']
            print(f"   🔑 Admin token obtained: {self.admin_token[:20]}...")
            return True
        elif success and 'token' in response:
            self.admin_token = response['token']
            print(f"   🔑 Admin token obtained: {self.admin_token[:20]}...")
            return True
        
        return False

    def run_test_with_admin_token(self, name, method, endpoint, expected_status, data=None, is_critical=False):
        """Run a test with admin token"""
        url = f"{self.api_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.admin_token:
            test_headers['Authorization'] = f'Bearer {self.admin_token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=10)

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"✅ PASSED - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict) and len(str(response_data)) < 300:
                        print(f"   Response: {response_data}")
                except:
                    pass
            else:
                print(f"❌ FAILED - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Raw response: {response.text[:200]}")
                
                failure_info = {
                    'name': name,
                    'expected': expected_status,
                    'actual': response.status_code,
                    'url': url,
                    'is_critical': is_critical
                }
                self.failed_tests.append(failure_info)
                
                if is_critical:
                    self.critical_issues.append(failure_info)

            return success, response.json() if response.content else {}

        except Exception as e:
            print(f"❌ FAILED - Error: {str(e)}")
            failure_info = {'name': name, 'error': str(e), 'is_critical': is_critical}
            self.failed_tests.append(failure_info)
            if is_critical:
                self.critical_issues.append(failure_info)
            return False, {}

    # ==================== REFERRAL TIERS TESTS ====================
    
    def test_referral_tiers_api(self):
        """Test referral tiers API endpoints"""
        print(f"\n{'='*50}")
        print("🔍 TESTING REFERRAL TIERS API")
        print(f"{'='*50}")
        
        # Test get all tiers
        success, response = self.run_test_with_admin_token(
            "Get Referral Tiers",
            "GET",
            "admin/referral-tiers/tiers",
            200,
            is_critical=True
        )
        
        if success:
            tiers = response.get('tiers', [])
            print(f"   📊 Found {len(tiers)} referral tiers")
            
            # Validate tier structure
            expected_tiers = ['Starter', 'Silver', 'Gold', 'Platinum', 'Ruby']
            found_tiers = [tier.get('tier_name') for tier in tiers]
            
            for expected_tier in expected_tiers:
                if expected_tier in found_tiers:
                    print(f"   ✅ Found tier: {expected_tier}")
                else:
                    print(f"   ❌ Missing tier: {expected_tier}")
            
            # Check tier percentages
            for tier in tiers:
                tier_name = tier.get('tier_name')
                percentage = tier.get('bonus_percentage')
                min_refs = tier.get('min_referrals')
                max_refs = tier.get('max_referrals')
                print(f"   💰 {tier_name}: {percentage}% ({min_refs}-{max_refs or '∞'} referrals)")
        
        return success

    def test_global_overrides_api(self):
        """Test global overrides (campaigns) API"""
        print(f"\n🔍 Testing Global Overrides API...")
        
        # Test get global overrides
        success, response = self.run_test_with_admin_token(
            "Get Global Overrides",
            "GET",
            "admin/referral-tiers/global-overrides",
            200,
            is_critical=True
        )
        
        if success:
            overrides = response.get('overrides', [])
            active_override = response.get('active_override')
            print(f"   📊 Found {len(overrides)} global overrides")
            if active_override:
                print(f"   🎯 Active override: {active_override.get('name')} ({active_override.get('bonus_percentage')}%)")
        
        # Test create global override
        now = datetime.now(timezone.utc)
        future_date = now + timedelta(days=7)
        
        create_success, create_response = self.run_test_with_admin_token(
            "Create Global Override",
            "POST",
            "admin/referral-tiers/global-overrides",
            200,
            data={
                "name": "Test Campaign",
                "bonus_percentage": 25.0,
                "start_date": now.isoformat(),
                "end_date": future_date.isoformat(),
                "description": "Test campaign for API testing",
                "is_active": True
            },
            is_critical=False
        )
        
        return success and create_success

    def test_client_overrides_api(self):
        """Test client overrides API"""
        print(f"\n🔍 Testing Client Overrides API...")
        
        # Test get client overrides
        success, response = self.run_test_with_admin_token(
            "Get Client Overrides",
            "GET",
            "admin/referral-tiers/client-overrides",
            200,
            is_critical=True
        )
        
        if success:
            overrides = response.get('overrides', [])
            print(f"   📊 Found {len(overrides)} client overrides")
        
        return success

    # ==================== PROMOTIONS TESTS ====================
    
    def test_promotions_active_api(self):
        """Test active promotions API (public endpoint)"""
        print(f"\n{'='*50}")
        print("🔍 TESTING PROMOTIONS API")
        print(f"{'='*50}")
        
        # Test public active promotions endpoint
        success, response = self.run_test(
            "Get Active Promotions (Public)",
            "GET",
            "promotions/active",
            200,
            is_critical=True
        )
        
        if success:
            promotions = response.get('promotions', [])
            count = response.get('count', 0)
            print(f"   📊 Found {count} active promotions")
            
            # Check for Summer Bonus Bash promotion
            summer_promo_found = False
            for promo in promotions:
                title = promo.get('title', '')
                if 'Summer Bonus Bash' in title:
                    summer_promo_found = True
                    print(f"   🎉 Found Summer Bonus Bash promotion!")
                    print(f"      Title: {title}")
                    print(f"      Subtitle: {promo.get('subtitle', 'N/A')}")
                    print(f"      CTA: {promo.get('cta_text', 'N/A')}")
                
                print(f"   🎯 Promotion: {title}")
            
            if not summer_promo_found:
                print(f"   ⚠️ Summer Bonus Bash promotion not found")
        
        return success

    def test_promotions_admin_api(self):
        """Test admin promotions API"""
        print(f"\n🔍 Testing Admin Promotions API...")
        
        # Test get all promotions (admin)
        success, response = self.run_test_with_admin_token(
            "Get All Promotions (Admin)",
            "GET",
            "promotions/admin/all",
            200,
            is_critical=True
        )
        
        if success:
            promotions = response.get('promotions', [])
            print(f"   📊 Found {len(promotions)} total promotions")
            
            # Check promotion statuses
            statuses = {}
            for promo in promotions:
                status = promo.get('status', 'unknown')
                statuses[status] = statuses.get(status, 0) + 1
            
            for status, count in statuses.items():
                print(f"   📈 {status.title()}: {count}")
        
        # Test create promotion
        now = datetime.now(timezone.utc)
        future_date = now + timedelta(days=1)
        
        create_success, create_response = self.run_test_with_admin_token(
            "Create Test Promotion",
            "POST",
            "promotions/admin",
            200,
            data={
                "title": "Test Promotion API",
                "subtitle": "Testing promotion creation",
                "cta_text": "Test Now",
                "background_color": "#8b5cf6",
                "text_color": "#ffffff",
                "priority": 1,
                "start_date": now.isoformat(),
                "end_date": future_date.isoformat(),
                "is_active": True
            },
            is_critical=False
        )
        
        # Test promotion stats
        stats_success, stats_response = self.run_test_with_admin_token(
            "Get Promotion Stats",
            "GET",
            "promotions/admin/stats",
            200,
            is_critical=False
        )
        
        if stats_success:
            stats = stats_response.get('stats', {})
            print(f"   📊 Promotion Stats:")
            print(f"      Active: {stats.get('active', 0)}")
            print(f"      Scheduled: {stats.get('scheduled', 0)}")
            print(f"      Total Views: {stats.get('total_views', 0)}")
            print(f"      Total Clicks: {stats.get('total_clicks', 0)}")
        
        return success and create_success

    # ==================== PAYMENT METHODS TEST ====================
    
    def test_payment_methods_api(self):
        """Test payment methods API"""
        print(f"\n{'='*50}")
        print("🔍 TESTING PAYMENT METHODS API")
        print(f"{'='*50}")
        
        success, response = self.run_test(
            "Get Payment Methods",
            "GET",
            "payments/methods",
            200,
            is_critical=True
        )
        
        if success:
            methods = response.get('methods', [])
            print(f"   📊 Found {len(methods)} payment methods")
            
            for method in methods:
                title = method.get('title', 'Unknown')
                qr_codes = method.get('qr_codes', [])
                print(f"   💳 {title}: {len(qr_codes)} QR codes")
        
        return success

    def print_summary(self):
        """Print test summary"""
        print(f"\n" + "="*60)
        print(f"📊 REFERRAL TIERS & PROMOTIONS TESTING SUMMARY")
        print(f"="*60)
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {len(self.failed_tests)}")
        print(f"Critical Issues: {len(self.critical_issues)}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")
        
        if self.critical_issues:
            print(f"\n🚨 CRITICAL ISSUES:")
            for issue in self.critical_issues:
                print(f"   • {issue['name']}")
                if 'expected' in issue:
                    print(f"     Expected: {issue['expected']}, Got: {issue['actual']}")
                if 'error' in issue:
                    print(f"     Error: {issue['error']}")
        
        if self.failed_tests:
            print(f"\n❌ ALL FAILED TESTS:")
            for test in self.failed_tests:
                priority = "🚨 CRITICAL" if test.get('is_critical') else "⚠️ MINOR"
                print(f"   {priority}: {test['name']}")
                if 'expected' in test:
                    print(f"     Expected: {test['expected']}, Got: {test['actual']}")
                if 'error' in test:
                    print(f"     Error: {test['error']}")
        
        # Determine if testing should continue
        critical_failure_rate = len(self.critical_issues) / max(1, self.tests_run)
        if critical_failure_rate > 0.5:
            print(f"\n🛑 RECOMMENDATION: More than 50% of critical tests failed.")
            print(f"   Main agent should fix critical issues before proceeding with frontend testing.")
            return False
        
        return len(self.critical_issues) == 0

def main():
    print("🚀 Starting Financial Gaming Platform - Referral Tiers & Promotions Testing")
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Focus: Referral Tier System, Promotions Banner, Login Functionality")
    
    tester = FinancialPlatformTester()
    
    # Test basic connectivity
    if not tester.test_health_check()[0]:
        print("❌ Health check failed - backend may not be running")
        tester.print_summary()
        return 1
    
    # Test user authentication (critical for client features)
    print(f"\n🔐 Testing user authentication...")
    user_auth_success = tester.test_user_login()
    
    # Test admin authentication (critical for admin features)
    print(f"\n🔐 Testing admin authentication...")
    admin_auth_success = tester.test_admin_login()
    
    # Test public APIs first
    print(f"\n🌐 Testing public APIs...")
    tester.test_promotions_active_api()
    tester.test_payment_methods_api()
    
    if admin_auth_success:
        print(f"\n🔐 Admin authentication successful, testing admin features...")
        
        # Test referral tiers system
        tester.test_referral_tiers_api()
        tester.test_global_overrides_api()
        tester.test_client_overrides_api()
        
        # Test admin promotions
        tester.test_promotions_admin_api()
    else:
        print(f"\n⚠️ Admin authentication failed - cannot test admin features")
        tester.critical_issues.append({
            'name': 'Admin Authentication Failed',
            'error': 'Cannot access admin features',
            'is_critical': True
        })
    
    if not user_auth_success:
        print(f"\n⚠️ User authentication failed - frontend login will not work")
        tester.critical_issues.append({
            'name': 'User Authentication Failed', 
            'error': 'Client login will not work',
            'is_critical': True
        })
    
    # Print final summary and determine next steps
    success = tester.print_summary()
    
    if len(tester.critical_issues) > 0:
        print(f"\n🔄 NEXT STEPS:")
        print(f"   1. Fix critical backend issues listed above")
        print(f"   2. Re-run backend tests to verify fixes")
        print(f"   3. Proceed with frontend testing once backend is stable")
        return 1
    else:
        print(f"\n✅ Backend tests passed! Ready for frontend testing.")
        return 0

if __name__ == "__main__":
    sys.exit(main())