import ResultViewLayout from './ResultViewLayout'
import { FolderOutlined, FileTextOutlined } from '@ant-design/icons'
import { Space } from 'antd'

// 资产负债预测表
// 固定列：层级 / 层级编码 / 账户册名称
// 分组列：M0~M24 × 4（余额 / 年日均 / 累计利息收支 / 累计收付息率%）
const mGroups = Array.from({ length: 25 }, (_, i) => ({
  title: `M${i}`,
  columns: [
    { title: '余额', key: 0, width: 110, type: 'money' as const },
    { title: '年日均', key: 1, width: 110, type: 'money' as const },
    { title: '累计利息收支', key: 2, width: 110, type: 'money' as const },
    { title: '累计收付息率(%)', key: 3, width: 95, type: 'percent' as const }
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
    key: 'coa_name', title: '账户册名称', width: 240, dataIndex: 'coa_name',
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
  }
]

const ResultForecastPage = () => (
  <ResultViewLayout
    endpoint="/result-view/forecast"
    title="资产负债预测表"
    description="账户册树形 + M0~M24 共 25 期（M0=当前存量；M1~M24 累计叠加业务计划）。"
    fixedColumns={fixedColumns}
    mGroups={mGroups}
  />
)

export default ResultForecastPage