import ResultViewLayout from './ResultViewLayout'
import { FolderOutlined, FileTextOutlined } from '@ant-design/icons'
import { Space } from 'antd'

// 策略看板（新增）：M0=当前存量；M1~M24 累计叠加业务计划 + 定价策略BP
const mGroups = Array.from({ length: 25 }, (_, i) => ({
  title: `M${i}`,
  columns: [
    { title: '期末余额', key: 0, width: 110, type: 'money' as const },
    { title: '月日均', key: 1, width: 110, type: 'money' as const },
    { title: '利息收支', key: 2, width: 110, type: 'money' as const },
    { title: '收付息率(%)', key: 3, width: 90, type: 'percent' as const }
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
    key: 'coa_name', title: '账户册', width: 240, dataIndex: 'coa_name',
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
    key: 'term', title: '期限维度', width: 90, dataIndex: 'term',
    render: (val: string) => val
      ? <span style={{ color: '#1890ff', fontWeight: 500 }}>{val}</span>
      : <span style={{ color: '#bbb' }}>-</span>
  }
]

const ResultStrategyBoardNewPage = () => (
  <ResultViewLayout
    endpoint="/result-view/strategy-board-new"
    title="策略看板（新增）"
    description="账户册树形 + M0~M24 共 25 期，M0=当前存量；M1~M24 累计叠加业务计划 + 定价策略 BP。"
    fixedColumns={fixedColumns}
    mGroups={mGroups}
  />
)

export default ResultStrategyBoardNewPage