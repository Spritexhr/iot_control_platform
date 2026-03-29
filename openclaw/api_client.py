import requests
import logging
import time

logger = logging.getLogger(__name__)

class IoTAPIClient:
    """
    IoT 平台 API 客户端 (支持 JWT 认证)
    """
    def __init__(self, base_url, username=None, password=None):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = 0  # 简单记录过期时间 (可选)

    @property
    def headers(self):
        """构造带有 Authorization 的请求头"""
        h = {"Content-Type": "application/json"}
        if self.access_token:
            h["Authorization"] = f"Bearer {self.access_token}"
        return h

    def login(self):
        """执行 JWT 登录并获取 access/refresh 令牌"""
        if not self.username or not self.password:
            logger.error("未配置用户名或密码，无法执行登录")
            return False

        url = f"{self.base_url}/auth/login/"
        payload = {
            "username": self.username,
            "password": self.password
        }

        try:
            logger.info(f"正在登录到 {url}...")
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # SimpleJWT 通常返回 access 和 refresh
            self.access_token = data.get("access")
            self.refresh_token = data.get("refresh")
            logger.info("登录成功，已获取 JWT 令牌")
            return True
        except Exception as e:
            logger.error(f"登录失败: {e}")
            return False

    def request(self, method, endpoint, **kwargs):
        """通用的请求封装，支持自动登录/重试"""
        url = f"{self.base_url}{endpoint}"
        
        # 如果没有令牌，先尝试登录
        if not self.access_token:
            if not self.login():
                return None

        try:
            response = requests.request(method, url, headers=self.headers, **kwargs)
            
            # 如果令牌失效 (401)，尝试重新登录并重试一次
            if response.status_code == 401:
                logger.warning("令牌失效，尝试重新登录...")
                if self.login():
                    response = requests.request(method, url, headers=self.headers, **kwargs)
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"API {method} 请求失败 [{url}]: {e}")
            return None

    def get(self, endpoint, params=None):
        return self.request("GET", endpoint, params=params)

    def post(self, endpoint, data=None):
        return self.request("POST", endpoint, json=data)

# 默认客户端实例
# 使用您的公网地址，并配置账号密码
api_client = IoTAPIClient(
    base_url="http://iot.gxmzucodeclub.top/api",
    username="xhr1", # 这里填入您的账号
    password="Solo/server678a"  # 这里填入您的密码
)
