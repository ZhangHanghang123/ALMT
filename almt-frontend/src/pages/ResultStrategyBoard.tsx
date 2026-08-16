import { useState, useEffect } from 'react'
import { Card, Table, Button, Space, message, Spin } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import apiClient from '../api/client'
import VersionSelector from '../components/VersionSelector'

interface TreeNode {
  key: string
  id?: number
  coa_cd: string
  coa_name: string | null
  has_data: boolean
  m0?: number[]
  m_values?: number[]   // 24 期 × 4 子列 = 96 个值
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
    return v.toFixed(2) + '%'
  }
}

const ResultStrategyBoardPage = () => {
  const [flatData, setFlatData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [version, setVersion] = useState<string>('')

  const fetchData = async () => {
    setLoading(true)
    try {
      const params = version ? { calc_version: version } : {}
      const res = await apiClient.get('/result-view/strategy-board', { params })
      // 把树形展平
      const flat: any[] = []
      const walk = (nodes: any[]) => {
        nodes.forEach(n => {
          flat.push({ ...n, key: `sb_${n.id || n.coa_cd}` })
          if (n.children && n.children.length > 0) walk(n.children)
        })
      }
      walk(res.data || [])
      setFlatData(flat)
    } catch (e: any) {
      message.error('加载策略看板失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [version])

  // 把每 M 的 4 子列（规模/日均/利息收支/收付息率）展开成表头
  const subCols = ['期末余额', '月日均', '利息收支', '收付息率']
  const mHeaders: any[] = [
    { title: 'M0', children: subCols.map(h => ({ title: h, key: 'm0_' + h, width: 90, align: 'right' as const })) }
  ]
  for (let i = 1; i <= 24; i++) {
    mHeaders.push({
      title: `M${i}`,
      children: subCols.map(h => ({
        title: h,
        key: `m${i}_` + h,
        width: 90,
        align: 'right' as const
      }))
    })
  }

  // 渲染每行
  const renderCell = (record: any, mIdx: number, subIdx: number) => {
    let v: number | undefined
    if (mIdx === 0) {
      v = record.m0?.[subIdx]
    } else {
      // m_values 是 24 × 4 = 96 个值
      v = record.m_values?.[(mIdx - 1) * 4 + subIdx]
    }
    if (v === undefined || v === 0) return <span style={{ color: '#bbb' }}>-</span>
    if (subIdx === 3) return <span style={{ color: '#1890ff' }}>{fmt.percent(v)}</span>
    return fmt.money(v)
  }

  const columns: any[] = [
    {
      title: '账户册编码',
      dataIndex: 'coa_cd',
      key: 'coa_cd',
      width: 180,
      fixed: 'left' as const,
      ellipsis: true,
      render: (v: string) => <span style={{ fontFamily: 'monospace', color: '#1890ff' }}>{v}</span>
    },
    {
      title: '账户册',
      dataIndex: 'coa_name',
      key: 'coa_name',
      width: 220,
      fixed: 'left' as const,
      ellipsis: true
    },
    {
      title: '条线',
      key: 'biz_line',
      width: 100,
      fixed: 'left' as const,
      render: () => '全行'
    },
    {
      title: '期限',
      key: 'term',
      width: 80,
      fixed: 'left' as const,
      render: () => '全部'
    },
    ...mHeaders.flatMap(m => m.children.map((c: any) => ({
      title: c.title,
      key: c.key,
      width: c.width,
      align: c.align,
      render: (_: any, r: any) => {
        const mIdx = mHeaders.findIndex(mm => mm.children.some((sc: any) => sc.key === c.key))
        const subIdx = m.children.findIndex((sc: any) => sc.key === c.key)
        return renderCell(r, mIdx, subIdx)
      }
    })))
  ]

  return (
    <div>
      <h2>结果查看 / 策略看板（累计）</h2>
      <Card style={{ marginBottom: 12 }}>
        <Space wrap>
          <VersionSelector value={version} onChange={setVersion} />
          <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
          <span style={{ color: '#666' }}>账户册 + 条线 + 期限 + M0~M24 每期 4 列（期末余额/月日均/利息收支/收付息率）</span>
        </Space>
      </Card>
      <Card bodyStyle={{ padding: 0 }}>
        <Spin spinning={loading}>
          <Table
            columns={columns}
            dataSource={flatData}
            rowKey="key"
            loading={loading}
            size="small"
            pagination={{ pageSize: 50, showSizeChanger: true, showTotal: (t) => `共 ${t} 条` }}
            scroll={{ x: 600 + 100 * 25, y: 700 }}
            bordered
          />
        </Spin>
      </Card>
    </div>
  )
}

export default ResultStrategyBoardPage