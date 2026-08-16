import { useState, useEffect, useMemo } from 'react'
import { Card, Table, Button, Space, message } from 'antd'
import { ReloadOutlined, LineChartOutlined, TableOutlined } from '@ant-design/icons'
import apiClient from '../api/client'
import VersionSelector from '../components/VersionSelector'

/**
 * 计算相邻相同值单元格的 rowSpan。
 * 第一个出现的行返回该组合并的行数，后续相同值的行返回 0（由 antd 隐藏）。
 */
const calcRowSpans = (rows: any[], field: string): number[] => {
  const sp: number[] = []
  let i = 0
  while (i < rows.length) {
    const val = rows[i][field]
    let count = 1
    let j = i + 1
    while (j < rows.length && rows[j][field] === val) {
      count++
      j++
    }
    sp.push(count)
    for (let k = 1; k < count; k++) sp.push(0)
    i = j
  }
  return sp
}

/** 居中单元格样式 */
const centerSpan = { textAlign: 'center' as const, verticalAlign: 'middle' as const, color: '#1890ff', fontWeight: 'bold' as const }

const formatNumber = (v: number | null | undefined) => {
  if (v === null || v === undefined) return '-'
  const abs = Math.abs(v)
  if (abs >= 1e8) return (v / 1e8).toFixed(2) + '亿'
  if (abs >= 1e4) return (v / 1e4).toFixed(2) + '万'
  return v.toFixed(4)
}

// 生成25列（M0 + M1~M24）
const m25Cols = (keyPrefix: string, onFormat = formatNumber): any[] => {
  const cols: any[] = []
  cols.push({
    title: 'M0', dataIndex: 'm0', key: `${keyPrefix}_m0`, width: 100, align: 'right' as const,
    render: onFormat
  })
  for (let i = 1; i <= 24; i++) {
    cols.push({
      title: `M${i}`,
      dataIndex: `m${i}`,
      key: `${keyPrefix}_m${i}`,
      width: 90,
      align: 'right' as const,
      render: onFormat
    })
  }
  return cols
}

const transformData = (items: any[]) => {
  return items.map((item, idx) => {
    const m_values = item.m_values || []
    const row: any = {
      key: idx,
      category: item.category,
      name: item.name,
      biz_line: item.biz_line,
      indicator: item.indicator,
      limit: item.limit || 0
    }
    m_values.forEach((v: number, i: number) => {
      row[`m${i}`] = v
    })
    return row
  })
}

const IndicatorPage = ({ defaultTab = '1' }: { defaultTab?: '1' | '2' }) => {
  const [fullBankData, setFullBankData] = useState<any[]>([])
  const [bizLineData, setBizLineData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'1' | '2'>(defaultTab)
  const [version, setVersion] = useState<string>('')

  const fetchFullBank = async () => {
    setLoading(true)
    try {
      const res = await apiClient.get('/indicator/full-bank', {
        params: version ? { calc_version: version } : {}
      })
      setFullBankData(Array.isArray(res.data) ? res.data : [])
    } catch (e) {
      message.error('加载全行指标失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchBizLine = async () => {
    setLoading(true)
    try {
      const res = await apiClient.get('/indicator/business-line', {
        params: version ? { calc_version: version } : {}
      })
      setBizLineData(Array.isArray(res.data) ? res.data : [])
    } catch (e) {
      message.error('加载条线指标失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (activeTab === '1') fetchFullBank()
    else fetchBizLine()
  }, [activeTab, version])

  // 转换后行
  const fullBankRows = useMemo(() => transformData(fullBankData), [fullBankData])
  const bizLineRows = useMemo(() => transformData(bizLineData), [bizLineData])

  // 分类合并行数
  const fullBankRowSpans = useMemo(() => calcRowSpans(fullBankRows, 'category'), [fullBankRows])
  // 条线合并行数
  const bizLineRowSpans = useMemo(() => calcRowSpans(bizLineRows, 'biz_line'), [bizLineRows])

  // 全行指标列
  const fullBankColumns: any[] = useMemo(() => [
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 180,
      fixed: 'left' as const,
      align: 'center' as const,
      onCell: (_record: any, index: number) => ({ rowSpan: fullBankRowSpans[index] ?? 1 }),
      render: (v: string) => <span style={centerSpan}>{v}</span>
    },
    {
      title: '指标名称',
      dataIndex: 'name',
      key: 'name',
      width: 220,
      fixed: 'left' as const,
      render: (v: string, record: any) => (
        <span style={{ fontWeight: record.category ? 'bold' : 'normal' }}>{v}</span>
      )
    },
    {
      title: '限额',
      dataIndex: 'limit',
      key: 'limit',
      width: 80,
      fixed: 'left' as const,
      align: 'right' as const,
      render: (v: number) => v
        ? <span style={{ color: '#cf1322' }}>{v.toFixed(4)}</span>
        : '-'
    },
    ...m25Cols('full')
  ], [fullBankRowSpans])

  // 条线指标列
  const bizLineColumns: any[] = useMemo(() => [
    {
      title: '条线',
      dataIndex: 'biz_line',
      key: 'biz_line',
      width: 140,
      fixed: 'left' as const,
      align: 'center' as const,
      onCell: (_record: any, index: number) => ({ rowSpan: bizLineRowSpans[index] ?? 1 }),
      render: (v: string) => <span style={centerSpan}>{v}</span>
    },
    {
      title: '指标',
      dataIndex: 'indicator',
      key: 'indicator',
      width: 140,
      fixed: 'left' as const
    },
    ...m25Cols('biz')
  ], [bizLineRowSpans])

  const items = [
    {
      key: '1',
      label: <span><TableOutlined /> 全行指标 ({fullBankData.length})</span>,
      children: (
        <div>
          <Space style={{ marginBottom: 16 }}>
            <Button icon={<ReloadOutlined />} onClick={fetchFullBank}>刷新</Button>
            <span style={{ color: '#666' }}>数据来源：{version ? `版本 ${version} 的 result_index` : '当前参数（almt_current_position + 业务计划 + 利率情景 + 风险权重）'}</span>
          </Space>
          <Table
            columns={fullBankColumns}
            dataSource={fullBankRows}
            loading={loading}
            size="small"
            scroll={{ x: 3000, y: 600 }}
            pagination={false}
            bordered
          />
        </div>
      )
    },
    {
      key: '2',
      label: <span><LineChartOutlined /> 条线指标 ({bizLineData.length})</span>,
      children: (
        <div>
          <Space style={{ marginBottom: 16 }}>
            <Button icon={<ReloadOutlined />} onClick={fetchBizLine}>刷新</Button>
            <span style={{ color: '#666' }}>按业务条线 + 指标维度展示 M0~M24 共25期数据（合并显示相同条线）</span>
          </Space>
          <Table
            columns={bizLineColumns}
            dataSource={bizLineRows}
            loading={loading}
            size="small"
            scroll={{ x: 3000, y: 600 }}
            pagination={false}
            bordered
          />
        </div>
      )
    }
  ]

  // 当前激活 Tab 的标题（用于页面 h2）
  const tabTitles: Record<string, string> = {
    '1': '全行指标',
    '2': '条线指标'
  }

  const currentTab = items.find(i => i.key === activeTab)

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>{tabTitles[activeTab]}（指标查询）</h2>
      <Card style={{ marginBottom: 16 }}>
        <VersionSelector value={version} onChange={setVersion} />
      </Card>
      <Card bordered={false} style={{ background: 'transparent' }}>
        {currentTab?.children}
      </Card>
    </div>
  )
}

export default IndicatorPage