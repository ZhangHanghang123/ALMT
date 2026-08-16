import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Layout, Menu } from 'antd'
import {
  DashboardOutlined,
  BankOutlined,
  SettingOutlined,
  DatabaseOutlined,
  CalculatorOutlined,
  BarChartOutlined,
  LogoutOutlined,
  ProfileOutlined,
  BookOutlined,
  LineChartOutlined,
  AppstoreOutlined,
  FundOutlined,
  PercentageOutlined,
  StockOutlined,
  TableOutlined,
  ApartmentOutlined,
  TagOutlined
} from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import COA from './pages/COA'
import Data from './pages/Data'
import Calculate from './pages/Calculate'
import Result from './pages/Result'
import ResultAllocationBalance from './pages/ResultAllocationBalance'
import ResultAllocationAverage from './pages/ResultAllocationAverage'
import ResultInterestNetIncome from './pages/ResultInterestNetIncome'
import ResultStrategyBoard from './pages/ResultStrategyBoard'
import ResultStrategyBoardNew from './pages/ResultStrategyBoardNew'
import ResultStrategyBoardStock from './pages/ResultStrategyBoardStock'
import ResultValueAnalysis from './pages/ResultValueAnalysis'
import ResultForecast from './pages/ResultForecast'
import ResultPricingStrategy from './pages/ResultPricingStrategy'
import BasicParam from './pages/BasicParam'
import Dict from './pages/Dict'
import ParamRateScenario from './pages/ParamRateScenario'
import ParamRiskWeight from './pages/ParamRiskWeight'
import ParamFtpMargin from './pages/ParamFtpMargin'
import ParamBusinessPlan from './pages/ParamBusinessPlan'
import ParamCustomStrategy from './pages/ParamCustomStrategy'
import IndicatorFullBank from './pages/IndicatorFullBank'
import IndicatorBizLine from './pages/IndicatorBizLine'

const { Header, Sider, Content } = Layout

const AppLayout = ({ children }: { children: React.ReactNode }) => {
  const navigate = useNavigate()
  const location = useLocation()

  // 当前激活菜单：精确匹配 path
  const selectedKey = location.pathname

  // 自动展开父菜单（参数配置 / 指标查询 / 结果查看）
  const openKeys: string[] = []
  if (location.pathname.startsWith('/param/')) openKeys.push('sub-param')
  if (location.pathname.startsWith('/indicator/')) openKeys.push('sub-indicator')
  if (location.pathname.startsWith('/result')) openKeys.push('sub-result')

  const menuItems = [
    { key: '/', icon: <DashboardOutlined />, label: '首页' },
    { key: '/coa', icon: <BankOutlined />, label: '账户册管理' },
    { key: '/basic-param', icon: <ProfileOutlined />, label: '基础参数' },
    { key: '/dict', icon: <BookOutlined />, label: '数据字典' },
    {
      key: 'sub-param',
      icon: <SettingOutlined />,
      label: '参数配置',
      children: [
        { key: '/param/rate', icon: <LineChartOutlined />, label: '利率情景' },
        { key: '/param/risk', icon: <PercentageOutlined />, label: '风险权重' },
        { key: '/param/ftp', icon: <StockOutlined />, label: 'FTP利差' },
        { key: '/param/business-plan', icon: <AppstoreOutlined />, label: '业务计划' },
        { key: '/param/custom-strategy', icon: <TagOutlined />, label: '定价策略' }
      ]
    },
    { key: '/data', icon: <DatabaseOutlined />, label: '存量数据' },
    { key: '/calculate', icon: <CalculatorOutlined />, label: '计算执行' },
    {
      key: 'sub-indicator',
      icon: <ApartmentOutlined />,
      label: '指标查询',
      children: [
        { key: '/indicator/full-bank', icon: <TableOutlined />, label: '全行指标' },
        { key: '/indicator/biz-line', icon: <FundOutlined />, label: '条线指标' }
      ]
    },
    {
      key: 'sub-result',
      icon: <BarChartOutlined />,
      label: '结果查看',
      children: [
        { key: '/result/allocation-balance', icon: <ProfileOutlined />, label: '中间表-分摊余额' },
        { key: '/result/allocation-average', icon: <ProfileOutlined />, label: '中间表-分摊日均' },
        { key: '/result/pricing-strategy', icon: <ProfileOutlined />, label: '中间表-定价策略' },
        { key: '/result/interest-net-income', icon: <ProfileOutlined />, label: '利息净收入测算' },
        { key: '/result/strategy-board-stock', icon: <ProfileOutlined />, label: '策略看板（存量）' },
        { key: '/result/strategy-board-new', icon: <ProfileOutlined />, label: '策略看板（新增）' },
        { key: '/result/strategy-board', icon: <ProfileOutlined />, label: '策略看板（累计）' },
        { key: '/result/value-analysis', icon: <ProfileOutlined />, label: '资负价值管理分析' },
        { key: '/result/forecast', icon: <ProfileOutlined />, label: '资产负债预测' },
        { key: '/result', icon: <ProfileOutlined />, label: '指标/计划结果' }
      ]
    }
  ]

  const handleLogout = () => {
    localStorage.removeItem('access_token')
    window.location.href = '/login'
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider theme="light" breakpoint="lg" collapsedWidth="0" width={220}>
        <div style={{ height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center', borderBottom: '1px solid #f0f0f0' }}>
          <h2 style={{ margin: 0, color: '#1890ff' }}>经营计划</h2>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          defaultOpenKeys={['sub-param', 'sub-indicator', 'sub-result']}
          items={menuItems}
          onClick={({ key }) => {
            // 父级菜单 key 不跳转
            if (key === 'sub-param' || key === 'sub-indicator' || key === 'sub-result') return
            navigate(key)
          }}
        />
        <div style={{ position: 'absolute', bottom: 16, width: '100%' }}>
          <Menu
            mode="inline"
            selectable={false}
            items={[
              { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: handleLogout }
            ]}
          />
        </div>
      </Sider>
      <Layout>
        <Header style={{ background: '#fff', padding: '0 24px', borderBottom: '1px solid #f0f0f0' }}>
          <h2 style={{ margin: 0 }}>经营计划模拟系统</h2>
        </Header>
        <Content style={{ margin: 24, padding: 24, background: '#fff', minHeight: 280 }}>
          {children}
        </Content>
      </Layout>
    </Layout>
  )
}

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const token = localStorage.getItem('access_token')
  if (!token) {
    return <Navigate to="/login" replace />
  }
  return <AppLayout>{children}</AppLayout>
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/coa" element={<ProtectedRoute><COA /></ProtectedRoute>} />
        <Route path="/basic-param" element={<ProtectedRoute><BasicParam /></ProtectedRoute>} />
        <Route path="/dict" element={<ProtectedRoute><Dict /></ProtectedRoute>} />

        {/* 参数配置：拆分 4 个独立路由 */}
        <Route path="/param/rate" element={<ProtectedRoute><ParamRateScenario /></ProtectedRoute>} />
        <Route path="/param/risk" element={<ProtectedRoute><ParamRiskWeight /></ProtectedRoute>} />
        <Route path="/param/ftp" element={<ProtectedRoute><ParamFtpMargin /></ProtectedRoute>} />
        <Route path="/param/business-plan" element={<ProtectedRoute><ParamBusinessPlan /></ProtectedRoute>} />
        <Route path="/param/custom-strategy" element={<ProtectedRoute><ParamCustomStrategy /></ProtectedRoute>} />

        <Route path="/data" element={<ProtectedRoute><Data /></ProtectedRoute>} />
        <Route path="/calculate" element={<ProtectedRoute><Calculate /></ProtectedRoute>} />

        {/* 指标查询：拆分 2 个独立路由 */}
        <Route path="/indicator/full-bank" element={<ProtectedRoute><IndicatorFullBank /></ProtectedRoute>} />
        <Route path="/indicator/biz-line" element={<ProtectedRoute><IndicatorBizLine /></ProtectedRoute>} />

        {/* 结果查看子路由 */}
        <Route path="/result/allocation-balance" element={<ProtectedRoute><ResultAllocationBalance /></ProtectedRoute>} />
        <Route path="/result/allocation-average" element={<ProtectedRoute><ResultAllocationAverage /></ProtectedRoute>} />
        <Route path="/result/pricing-strategy" element={<ProtectedRoute><ResultPricingStrategy /></ProtectedRoute>} />
        <Route path="/result/interest-net-income" element={<ProtectedRoute><ResultInterestNetIncome /></ProtectedRoute>} />
        <Route path="/result/strategy-board-stock" element={<ProtectedRoute><ResultStrategyBoardStock /></ProtectedRoute>} />
        <Route path="/result/strategy-board-new" element={<ProtectedRoute><ResultStrategyBoardNew /></ProtectedRoute>} />
        <Route path="/result/strategy-board" element={<ProtectedRoute><ResultStrategyBoard /></ProtectedRoute>} />
        <Route path="/result/value-analysis" element={<ProtectedRoute><ResultValueAnalysis /></ProtectedRoute>} />
        <Route path="/result/forecast" element={<ProtectedRoute><ResultForecast /></ProtectedRoute>} />
        <Route path="/result" element={<ProtectedRoute><Result /></ProtectedRoute>} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
