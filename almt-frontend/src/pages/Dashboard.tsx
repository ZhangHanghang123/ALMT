import { useState, useEffect } from 'react'
import { Card, Row, Col, Statistic } from 'antd'
import {
  BankOutlined,
  SettingOutlined,
  DatabaseOutlined,
  CalculatorOutlined,
  BarChartOutlined
} from '@ant-design/icons'

const Dashboard = () => {
  const [stats, setStats] = useState({
    coaCount: 0,
    paramCount: 0,
    taskCount: 0
  })

  useEffect(() => {
    // 加载统计数据
  }, [])

  return (
    <div>
      <h1 style={{ marginBottom: 24 }}>欢迎使用经营计划模拟系统</h1>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="账户册数量"
              value={stats.coaCount}
              prefix={<BankOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="参数配置"
              value={stats.paramCount}
              prefix={<SettingOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="计算任务"
              value={stats.taskCount}
              prefix={<CalculatorOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="数据指标"
              value={0}
              prefix={<BarChartOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col span={24}>
          <Card title="系统功能">
            <Row gutter={[16, 16]}>
              <Col xs={24} sm={12} md={8}>
                <Card size="small" hoverable>
                  <BankOutlined style={{ fontSize: 24, color: '#1890ff' }} />
                  <h3>账户册管理</h3>
                  <p>维护银行科目层级结构</p>
                </Card>
              </Col>
              <Col xs={24} sm={12} md={8}>
                <Card size="small" hoverable>
                  <SettingOutlined style={{ fontSize: 24, color: '#52c41a' }} />
                  <h3>参数配置</h3>
                  <p>利率情景、风险权重等</p>
                </Card>
              </Col>
              <Col xs={24} sm={12} md={8}>
                <Card size="small" hoverable>
                  <DatabaseOutlined style={{ fontSize: 24, color: '#faad14' }} />
                  <h3>存量数据</h3>
                  <p>导入和管理业务数据</p>
                </Card>
              </Col>
              <Col xs={24} sm={12} md={8}>
                <Card size="small" hoverable>
                  <CalculatorOutlined style={{ fontSize: 24, color: '#f5222d' }} />
                  <h3>计算执行</h3>
                  <p>执行经营计划模拟任务</p>
                </Card>
              </Col>
              <Col xs={24} sm={12} md={8}>
                <Card size="small" hoverable>
                  <BarChartOutlined style={{ fontSize: 24, color: '#722ed1' }} />
                  <h3>结果查看</h3>
                  <p>指标看板与策略看板</p>
                </Card>
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default Dashboard
