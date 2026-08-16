import { useState, useEffect } from 'react'
import { Card, Table, Tabs, Button, Space, Row, Col, Statistic, message, Empty, Tag } from 'antd'
import {
  ReloadOutlined, DollarOutlined, FundOutlined, BarChartOutlined,
  FileTextOutlined, FolderOutlined, FileTextOutlined as FileIcon
} from '@ant-design/icons'
import apiClient from '../api/client'
import VersionSelector from '../components/VersionSelector'

interface TreeNode {
  key: string
  id?: number
  coa_cd: string
  coa_name: string | null
  has_data: boolean
  children?: TreeNode[]
  [k: string]: any
}

const ResultPage = () => {
  const [selectedVersion, setSelectedVersion] = useState<string>('')
  const [summary, setSummary] = useState<any>(null)
  const [indexTree, setIndexTree] = useState<TreeNode[]>([])
  const [planTree, setPlanTree] = useState<TreeNode[]>([])
  const [loading, setLoading] = useState(false)
  const [dataInfo, setDataInfo] = useState<{task_id?: string, calc_version?: string, data_date?: string}>({})

  // 展开状态
  const [indexExpanded, setIndexExpanded] = useState<React.Key[]>([])
  const [planExpanded, setPlanExpanded] = useState<React.Key[]>([])
  const [tableKey, setTableKey] = useState(0)

  const collectAllKeys = (nodes: TreeNode[]): React.Key[] => {
    const keys: React.Key[] = []
    const walk = (list: TreeNode[]) => {
      list.forEach(n => {
        if (n.children && n.children.length > 0) {
          keys.push(n.key)
          walk(n.children)
        }
      })
    }
    walk(nodes)
    return keys
  }

  const convertKeys = (nodes: any[]): TreeNode[] =>
    nodes.map(n => ({
      ...n,
      key: `res_${n.id}`,
      id: n.id,
      children: n.children ? convertKeys(n.children) : undefined
    }))

  const fmtMoney = (v: number | null) => {
    if (v == null) return '-'
    if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(2) + ' 亿'
    if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(2) + ' 万'
    return v.toFixed(2)
  }

  const fetchResults = async (version?: string) => {
    setLoading(true)
    try {
      const params = version ? { calc_version: version } : {}
      const [sumRes, idxRes, planRes] = await Promise.all([
        apiClient.get('/result/summary', { params }),
        apiClient.get('/result/index/tree', { params }),
        apiClient.get('/result/plan/tree', { params }),
      ])
      setSummary(sumRes.data)
      setDataInfo({
        task_id: sumRes.data?.task_id,
        calc_version: sumRes.data?.calc_version || version,
        data_date: sumRes.data?.data_date,
      })
      const idxConverted = convertKeys(idxRes.data?.items || [])
      const planConverted = convertKeys(planRes.data?.items || [])
      setIndexTree(idxConverted)
      setPlanTree(planConverted)
      setIndexExpanded(collectAllKeys(idxConverted))
      setPlanExpanded(collectAllKeys(planConverted))
      setTableKey(k => k + 1)
    } catch (e: any) {
      message.error('加载结果失败: ' + (e.response?.data?.detail || e.message))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchResults(selectedVersion)
  }, [selectedVersion])

  const indexColumns = [
    {
      title: '层级编码', dataIndex: 'coa_cd', key: 'coa_cd', width: 180, ellipsis: true,
      render: (val: string, record: TreeNode) => (
        <span style={{ fontFamily: 'monospace', whiteSpace: 'nowrap', fontWeight: record.has_data ? 'bold' : 'normal' }}>
          {val}
        </span>
      )
    },
    {
      title: '账户册名称', dataIndex: 'coa_name', key: 'coa_name', ellipsis: true,
      render: (val: string, record: TreeNode) => (
        <Space>
          {record.has_data ? <FileIcon style={{ color: '#1890ff' }} /> : <FolderOutlined style={{ color: '#999' }} />}
          <span style={{ color: record.has_data ? 'inherit' : '#999', whiteSpace: 'nowrap' }}>{val || '-'}</span>
        </Space>
      )
    },
    {
      title: '余额', dataIndex: 'total_balance', key: 'total_balance', width: 150, align: 'right' as const,
      render: (val: number | null, record: TreeNode) => (
        <span style={{ color: record.has_data ? 'inherit' : '#bbb', fontWeight: record.has_data ? 'bold' : 'normal' }}>
          {record.has_data && val !== null ? fmtMoney(val) : '-'}
        </span>
      )
    },
    {
      title: '日均余额', dataIndex: 'average_balance', key: 'average_balance', width: 150, align: 'right' as const,
      render: (val: number | null, record: TreeNode) => (
        <span style={{ color: record.has_data ? 'inherit' : '#bbb', fontWeight: record.has_data ? 'bold' : 'normal' }}>
          {record.has_data && val !== null ? fmtMoney(val) : '-'}
        </span>
      )
    },
    {
      title: '平均利率', dataIndex: 'avg_rate', key: 'avg_rate', width: 120, align: 'right' as const,
      render: (val: number | null, record: TreeNode) => {
        if (!record.has_data || val === null) return <span style={{ color: '#bbb' }}>-</span>
        if (val > 0 && val < 1) return (Number(val) * 100).toFixed(2) + '%'
        return val.toFixed(2)
      }
    }
  ]

  const planColumns = [
    {
      title: '账户册编码', dataIndex: 'coa_cd', key: 'coa_cd', width: 180, ellipsis: true,
      render: (val: string, record: TreeNode) => (
        <span style={{ fontFamily: 'monospace', whiteSpace: 'nowrap', fontWeight: record.has_data ? 'bold' : 'normal' }}>
          {val}
        </span>
      )
    },
    {
      title: '账户册名称', dataIndex: 'coa_name', key: 'coa_name', ellipsis: true,
      render: (val: string, record: TreeNode) => (
        <Space>
          {record.has_data ? <FileIcon style={{ color: '#1890ff' }} /> : <FolderOutlined style={{ color: '#999' }} />}
          <span style={{ color: record.has_data ? 'inherit' : '#999', whiteSpace: 'nowrap' }}>{val || '-'}</span>
        </Space>
      )
    },
    {
      title: '计划余额', dataIndex: 'item_value', key: 'item_value', width: 200, align: 'right' as const,
      render: (val: number | null, record: TreeNode) => (
        <span style={{ color: record.has_data ? 'inherit' : '#bbb', fontWeight: record.has_data ? 'bold' : 'normal' }}>
          {record.has_data && val !== null ? fmtMoney(val) : '-'}
        </span>
      )
    }
  ]

  const tabItems = [
    {
      key: '1',
      label: <span><BarChartOutlined /> 基础指标</span>,
      children: (
        <Table
          key={`idx-${tableKey}`}
          rowKey="key"
          columns={indexColumns}
          dataSource={indexTree}
          loading={loading}
          size="small"
          pagination={false}
          scroll={{ y: 500 }}
          bordered
          expandable={{
            indentSize: 20,
            expandedRowKeys: indexExpanded,
            onExpand: (expanded, record) => {
              setIndexExpanded(prev =>
                expanded ? [...prev, record.key] : prev.filter(k => k !== record.key)
              )
            }
          }}
        />
      )
    },
    {
      key: '2',
      label: <span><FileTextOutlined /> 业务计划结果</span>,
      children: (
        <Table
          key={`plan-${tableKey}`}
          rowKey="key"
          columns={planColumns}
          dataSource={planTree}
          loading={loading}
          size="small"
          pagination={false}
          scroll={{ y: 500 }}
          bordered
          expandable={{
            indentSize: 20,
            expandedRowKeys: planExpanded,
            onExpand: (expanded, record) => {
              setPlanExpanded(prev =>
                expanded ? [...prev, record.key] : prev.filter(k => k !== record.key)
              )
            }
          }}
        />
      )
    }
  ]

  return (
    <div>
      <h2>结果查看</h2>

      <Card style={{ marginBottom: 16 }}>
        <Space>
          <VersionSelector value={selectedVersion} onChange={setSelectedVersion} />
          <Button icon={<ReloadOutlined />} onClick={() => fetchResults(selectedVersion)}>刷新</Button>
          {dataInfo.calc_version && (
            <Tag color="blue" style={{ fontFamily: 'monospace' }}>
              当前：{dataInfo.calc_version} {dataInfo.data_date ? `(${dataInfo.data_date})` : ''}
            </Tag>
          )}
        </Space>
      </Card>

      {summary && summary.task_id ? (
        <>
          <Card title="汇总指标" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col span={6}>
                <Statistic
                  title="数据日期"
                  value={summary.data_date || '-'}
                  prefix={<FundOutlined />}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="总资产"
                  value={(summary.total_assets || 0) / 1e8}
                  precision={2}
                  suffix="亿"
                  valueStyle={{ color: '#3f8600' }}
                  prefix={<DollarOutlined />}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="总负债"
                  value={Math.abs(summary.total_liabilities || 0) / 1e8}
                  precision={2}
                  suffix="亿"
                  valueStyle={{ color: '#cf1322' }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="净资产"
                  value={(summary.net_position || 0) / 1e8}
                  precision={2}
                  suffix="亿"
                  valueStyle={{ color: '#1890ff' }}
                />
              </Col>
            </Row>
            <Row gutter={16} style={{ marginTop: 16 }}>
              <Col span={6}>
                <Statistic
                  title="平均利率"
                  value={(summary.avg_rate || 0) * 100}
                  precision={2}
                  suffix="%"
                />
              </Col>
              <Col span={6}>
                <Statistic title="指标节点数" value={summary.index_count || 0} suffix=" 个" />
              </Col>
            </Row>
          </Card>

          <Card>
            <Tabs items={tabItems} />
          </Card>
        </>
      ) : (
        <Card>
          <Empty
            description={
              selectedVersion
                ? `版本 ${selectedVersion} 暂无结果数据`
                : '请选择一个计算版本'
            }
          />
        </Card>
      )}
    </div>
  )
}

export default ResultPage