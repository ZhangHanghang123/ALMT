import ResultViewLayout from './ResultViewLayout'
import { FolderOutlined, FileTextOutlined } from '@ant-design/icons'
import { Space } from 'antd'

// 中间表-定价策略
// 固定列：层级 / 层级编码 / 账户册 / 条线维度 / 原始期限 / 当前平均利率% / 当前曲线值%
// 分组列：M1~M24 × 5（条线预报值%/曲线值%/变动值BP/调整BP/定价策略%）-- 24 组
const mGroups = Array.from({ length: 24 }, (_, i) => ({
  title: `M${i + 1}`,
  columns: [
    { title: '条线预报值(%)', key: 0, width: 88, type: 'percent' as const },
    { title: '曲线值(%)', key: 1, width: 80, type: 'percent' as const },
    { title: '变动值(△BP)', key: 2, width: 80, type: 'bp' as const },
    { title: '调整(△BP)', key: 3, width: 80, type: 'bp' as const,
      color: (v: number) => v > 0 ? '#cf1322' : (v < 0 ? '#3f8600' : '#bbb') },
    { title: '定价策略(%)', key: 4, width: 85, type: 'percent' as const }
  ]
}))

const fixedColumns = [
  {
    key: 'level', title: '层级', width: 70, dataIndex: 'level',
    render: (val: any) => <span style={{ color: '#666' }}>{val}</span>
  },
  {
    key: 'coa_cd', title: '层级编码', width: 200, dataIndex: 'coa_cd',
    render: (val: string, record: any) => {
      const isRoot = record.coa_cd === 'ROOT'
      const hasChildren = record.children && record.children.length > 0
      const color = isRoot ? '#722ed1' : '#1890ff'
      const weight = isRoot || hasChildren ? 'bold' : 'normal'
      return <span style={{ fontFamily: 'monospace', whiteSpace: 'nowrap', color, fontWeight: weight }}>{val}</span>
    }
  },
  {
    key: 'coa_name', title: '账户册', width: 220, dataIndex: 'coa_name',
    render: (val: string, record: any) => {
      const isRoot = record.coa_cd === 'ROOT'
      const hasChildren = record.children && record.children.length > 0
      const Icon = hasChildren ? FolderOutlined : FileTextOutlined
      const iconColor = isRoot ? '#722ed1' : (record.has_data ? '#1890ff' : '#bbb')
      const textColor = isRoot ? '#722ed1' : (record.has_data ? 'inherit' : '#999')
      const fontWeight = isRoot || hasChildren ? 'bold' : 'normal'
      return (
        <Space size={6} style={{ whiteSpace: 'nowrap' }}>
          <Icon style={{ color: iconColor, fontSize: 13 }} />
          <span style={{ color: textColor, fontWeight }}>{val || '-'}</span>
        </Space>
      )
    }
  },
  {
    key: 'biz_line', title: '条线维度', width: 100, dataIndex: 'biz_line',
    render: (val: string) => <span style={{ color: '#666' }}>{val || '-'}</span>
  },
  {
    key: 'term', title: '原始期限', width: 90, dataIndex: 'term',
    render: (val: string) => val
      ? <span style={{ color: '#1890ff', fontWeight: 500 }}>{val}</span>
      : <span style={{ color: '#bbb' }}>-</span>
  },
  {
    key: 'cur_rate', title: '当前平均利率(%)', width: 110, dataIndex: 'cur_rate',
    render: (val: number, record: any) => {
      const v = record.m_values?.[0]
      if (v === undefined) return <span style={{ color: '#bbb' }}>-</span>
      return <span style={{ color: v === 0 ? '#bbb' : '#1890ff' }}>{v.toFixed(4)}%</span>
    }
  },
  {
    key: 'next_rate', title: '当前曲线值(%)', width: 110, dataIndex: 'next_rate',
    render: (val: number, record: any) => {
      const v = record.m_values?.[1]
      if (v === undefined) return <span style={{ color: '#bbb' }}>-</span>
      return <span style={{ color: v === 0 ? '#bbb' : '#52c41a' }}>{v.toFixed(4)}%</span>
    }
  }
]

const ResultPricingStrategyPage = () => (
  <ResultViewLayout
    endpoint="/result-view/pricing-strategy"
    title="中间表-定价策略"
    description="账户册树形 + M1~M24 共 24 期 × 5 列（条线预报值/曲线值/变动值/调整/定价策略）；当前平均利率 + 当前曲线值作为固定列。"
    fixedColumns={fixedColumns}
    mGroups={mGroups}
    mGroupsCount={24}
  />
)

export default ResultPricingStrategyPage