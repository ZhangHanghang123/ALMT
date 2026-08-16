import { useState, useEffect } from 'react'
import { Card, Table, Button, Space, message } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import apiClient from '../api/client'
import VersionSelector from '../components/VersionSelector'

interface TreeNode {
  key: string
  id?: number
  coa_cd: string
  coa_name: string | null
  has_data: boolean
  biz_line?: string
  cur_rate?: number
  next_rate?: number
  next_scale_balance?: number
  next_scale_avg?: number
  next_scale_change?: number
  children?: TreeNode[]
}

const fmt = {
  money: (v: number | null | undefined) => {
    if (v == null || v === 0) return '-'
    const abs = Math.abs(v)
    if (abs >= 1e8) return (v / 1e8).toFixed(2) + ' 亿'
    if (abs >= 1e4) return (v / 1e4).toFixed(2) + ' 万'
    return v.toFixed(2)
  },
  percent: (v: number | null | undefined) => {
    if (v == null) return '-'
    return v.toFixed(4) + '%'
  }
}

const ResultValueAnalysisPage = () => {
  const [flatData, setFlatData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [version, setVersion] = useState<string>('')

  const fetchData = async () => {
    setLoading(true)
    try {
      const params = version ? { calc_version: version } : {}
      const res = await apiClient.get('/result-view/value-analysis', { params })
      // 把树形展平
      const flat: any[] = []
      const walk = (nodes: any[]) => {
        nodes.forEach(n => {
          flat.push({ ...n, key: `va_${n.id || n.coa_cd}` })
          if (n.children && n.children.length > 0) walk(n.children)
        })
      }
      walk(res.data || [])
      setFlatData(flat)
    } catch (e) {
      message.error('加载价值分析失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchData() }, [version])

  const columns = [
    {
      title: '自定义层级',
      dataIndex: 'coa_lvl',
      key: 'coa_lvl',
      width: 100,
      render: (_: any, _r: any, idx: number) => idx + 1
    },
    {
      title: '层级编码',
      dataIndex: 'coa_cd',
      key: 'coa_cd',
      width: 180,
      render: (v: string) => <span style={{ fontFamily: 'monospace', color: '#1890ff' }}>{v}</span>
    },
    {
      title: '账户册',
      dataIndex: 'coa_name',
      key: 'coa_name',
      width: 220,
      ellipsis: true
    },
    {
      title: '条线',
      dataIndex: 'biz_line',
      key: 'biz_line',
      width: 120,
      render: (v: string) => v || '全行'
    },
    {
      title: '价格（当月利率）',
      key: 'cur_rate',
      width: 130,
      align: 'right' as const,
      render: (_: any, r: TreeNode) => fmt.percent(r.cur_rate)
    },
    {
      title: '价格（下月利率）',
      key: 'next_rate',
      width: 130,
      align: 'right' as const,
      render: (_: any, r: TreeNode) => fmt.percent(r.next_rate)
    },
    {
      title: '规模余额',
      key: 'next_scale_balance',
      width: 140,
      align: 'right' as const,
      render: (_: any, r: TreeNode) => fmt.money(r.next_scale_balance)
    },
    {
      title: '规模日均',
      key: 'next_scale_avg',
      width: 140,
      align: 'right' as const,
      render: (_: any, r: TreeNode) => fmt.money(r.next_scale_avg)
    },
    {
      title: '规模变动',
      key: 'next_scale_change',
      width: 120,
      align: 'right' as const,
      render: (_: any, r: TreeNode) => fmt.money(r.next_scale_change)
    }
  ]

  return (
    <div>
      <h2>结果查看 / 资负价值管理分析表</h2>
      <Card style={{ marginBottom: 12 }}>
        <Space wrap>
          <VersionSelector value={version} onChange={setVersion} />
          <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
          <span style={{ color: '#666' }}>账户册 + 条线 + 当月/下月利率 + 规模（余额/日均/变动）</span>
        </Space>
      </Card>
      <Card bodyStyle={{ padding: 0 }}>
        <Table
          columns={columns}
          dataSource={flatData}
          rowKey="key"
          loading={loading}
          size="small"
          pagination={{ pageSize: 50, showSizeChanger: true, showTotal: (t) => `共 ${t} 条` }}
          scroll={{ x: 1300, y: 700 }}
          bordered
        />
      </Card>
    </div>
  )
}

export default ResultValueAnalysisPage