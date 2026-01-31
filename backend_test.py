#!/usr/bin/env python3
"""
Blaze AI Bot Backend API Testing
Tests all endpoints for the Blaze Double pattern analysis system
"""

import requests
import sys
import json
from datetime import datetime
import time

class BlazeAPITester:
    def __init__(self, base_url="https://intelligent-audit-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details="", response_data=None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details,
            "response_data": response_data
        })

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)

        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        print(f"   Method: {method}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=30)

            print(f"   Status: {response.status_code}")
            
            success = response.status_code == expected_status
            response_data = None
            
            try:
                response_data = response.json()
                if success:
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
            except:
                response_data = response.text[:200] if response.text else "No response body"
                print(f"   Response: {response_data}")

            if not success:
                self.log_test(name, False, f"Expected {expected_status}, got {response.status_code}. Response: {response_data}", response_data)
            else:
                self.log_test(name, True, "", response_data)

            return success, response_data

        except requests.exceptions.Timeout:
            self.log_test(name, False, "Request timeout (30s)", None)
            return False, {}
        except Exception as e:
            self.log_test(name, False, f"Request error: {str(e)}", None)
            return False, {}

    def test_health_endpoints(self):
        """Test basic health endpoints"""
        print("\n" + "="*50)
        print("TESTING HEALTH ENDPOINTS")
        print("="*50)
        
        # Test root endpoint
        self.run_test("Root Endpoint", "GET", "", 200)
        
        # Test health endpoint
        self.run_test("Health Check", "GET", "health", 200)

    def test_auth_endpoints(self):
        """Test authentication endpoints"""
        print("\n" + "="*50)
        print("TESTING AUTHENTICATION")
        print("="*50)
        
        # Test login with test user
        login_data = {
            "email": "test@blaze.com",
            "password": "test123"
        }
        
        success, response = self.run_test("Login Test User", "POST", "auth/login", 200, login_data)
        
        if success and response and 'access_token' in response:
            self.token = response['access_token']
            self.user_id = response.get('user', {}).get('id')
            print(f"   ✅ Token obtained: {self.token[:20]}...")
            print(f"   ✅ User ID: {self.user_id}")
        else:
            print("   ❌ Failed to get token - will try to register")
            
            # Try to register the test user
            register_data = {
                "email": "test@blaze.com",
                "password": "test123",
                "name": "Test User"
            }
            
            success, response = self.run_test("Register Test User", "POST", "auth/register", 200, register_data)
            
            if success and response and 'access_token' in response:
                self.token = response['access_token']
                self.user_id = response.get('user', {}).get('id')
                print(f"   ✅ Token obtained after registration: {self.token[:20]}...")
            else:
                print("   ❌ Failed to register - authentication tests will fail")
                return False

        # Test /auth/me endpoint
        if self.token:
            self.run_test("Get Current User", "GET", "auth/me", 200)
        
        return True

    def test_prediction_endpoints(self):
        """Test prediction and AI analysis endpoints"""
        print("\n" + "="*50)
        print("TESTING PREDICTION ENDPOINTS")
        print("="*50)
        
        if not self.token:
            print("❌ No token available - skipping prediction tests")
            return
        
        # Test get prediction (this is the main AI analysis endpoint)
        print("🤖 Testing AI Analysis (may take 10-15 seconds)...")
        success, response = self.run_test("Get AI Prediction", "GET", "prediction", 200)
        
        if success and response:
            # Validate prediction structure
            required_fields = ['recommended_color', 'red_probability', 'black_probability', 
                             'white_probability', 'confidence', 'martingale_levels', 'ai_analysis']
            
            missing_fields = [field for field in required_fields if field not in response]
            if missing_fields:
                self.log_test("Prediction Structure Validation", False, f"Missing fields: {missing_fields}")
            else:
                self.log_test("Prediction Structure Validation", True)
                
                # Check if AI analysis is working
                ai_analysis = response.get('ai_analysis', '')
                if len(ai_analysis) > 50 and 'Carregando' not in ai_analysis:
                    self.log_test("AI Analysis Content", True, "AI analysis generated successfully")
                else:
                    self.log_test("AI Analysis Content", False, f"AI analysis seems incomplete: {ai_analysis[:100]}")

    def test_result_endpoints(self):
        """Test game result endpoints"""
        print("\n" + "="*50)
        print("TESTING RESULT ENDPOINTS")
        print("="*50)
        
        if not self.token:
            print("❌ No token available - skipping result tests")
            return
        
        # Test adding results
        for color in ['red', 'black', 'white']:
            result_data = {"color": color}
            self.run_test(f"Add {color.upper()} Result", "POST", "result", 200, result_data)
        
        # Test getting results
        self.run_test("Get Recent Results", "GET", "results?limit=10", 200)

    def test_history_endpoints(self):
        """Test history endpoints"""
        print("\n" + "="*50)
        print("TESTING HISTORY ENDPOINTS")
        print("="*50)
        
        if not self.token:
            print("❌ No token available - skipping history tests")
            return
        
        self.run_test("Get Prediction History", "GET", "history?limit=20", 200)

    def test_statistics_endpoints(self):
        """Test statistics endpoints"""
        print("\n" + "="*50)
        print("TESTING STATISTICS ENDPOINTS")
        print("="*50)
        
        if not self.token:
            print("❌ No token available - skipping statistics tests")
            return
        
        # Test main statistics
        success, response = self.run_test("Get User Statistics", "GET", "statistics", 200)
        
        if success and response:
            # Validate statistics structure
            required_fields = ['total_predictions', 'wins', 'losses', 'pending', 'win_rate']
            missing_fields = [field for field in required_fields if field not in response]
            if missing_fields:
                self.log_test("Statistics Structure Validation", False, f"Missing fields: {missing_fields}")
            else:
                self.log_test("Statistics Structure Validation", True)
        
        # Test chart data
        self.run_test("Get Chart Data", "GET", "chart-data?days=7", 200)

    def test_settings_endpoints(self):
        """Test settings endpoints"""
        print("\n" + "="*50)
        print("TESTING SETTINGS ENDPOINTS")
        print("="*50)
        
        if not self.token:
            print("❌ No token available - skipping settings tests")
            return
        
        # Test get settings
        success, response = self.run_test("Get User Settings", "GET", "settings", 200)
        
        if success and response:
            # Test update settings
            updated_settings = {
                "max_martingales": 3,
                "min_probability": 75,
                "notifications_enabled": True,
                "sound_enabled": False
            }
            
            self.run_test("Update User Settings", "PUT", "settings", 200, updated_settings)

    def test_error_cases(self):
        """Test error handling"""
        print("\n" + "="*50)
        print("TESTING ERROR CASES")
        print("="*50)
        
        # Test invalid login
        invalid_login = {"email": "invalid@test.com", "password": "wrongpass"}
        self.run_test("Invalid Login", "POST", "auth/login", 401, invalid_login)
        
        # Test unauthorized access (without token)
        old_token = self.token
        self.token = None
        self.run_test("Unauthorized Access", "GET", "prediction", 401)
        self.token = old_token
        
        # Test invalid result color
        if self.token:
            invalid_result = {"color": "invalid_color"}
            self.run_test("Invalid Result Color", "POST", "result", 400, invalid_result)

    def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting Blaze AI Bot Backend API Tests")
        print(f"🌐 Base URL: {self.base_url}")
        print(f"🔗 API URL: {self.api_url}")
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run test suites
        self.test_health_endpoints()
        
        auth_success = self.test_auth_endpoints()
        if auth_success:
            self.test_prediction_endpoints()
            self.test_result_endpoints()
            self.test_history_endpoints()
            self.test_statistics_endpoints()
            self.test_settings_endpoints()
        
        self.test_error_cases()
        
        # Print final results
        print("\n" + "="*60)
        print("FINAL TEST RESULTS")
        print("="*60)
        print(f"📊 Tests Run: {self.tests_run}")
        print(f"✅ Tests Passed: {self.tests_passed}")
        print(f"❌ Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"📈 Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        # Show failed tests
        failed_tests = [test for test in self.test_results if not test['success']]
        if failed_tests:
            print(f"\n❌ FAILED TESTS ({len(failed_tests)}):")
            for test in failed_tests:
                print(f"   • {test['test']}: {test['details']}")
        
        return self.tests_passed == self.tests_run

def main():
    """Main test execution"""
    tester = BlazeAPITester()
    
    try:
        success = tester.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())