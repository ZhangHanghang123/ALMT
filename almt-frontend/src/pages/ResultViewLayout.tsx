import { useState, useEffect, useMemo } from 'react'
import { Card, Table, Button, Space, message, Spin, Tooltip } from 'antd'
import { ReloadOutlined, DownloadOutlined, FolderOutlined, FileTextOutlined } from '@ant-design/icons'
import apiClient from '../api/client'
import VersionSelector from '../components/VersionSelector'

interface TreeNode {
  key: string
  id?: number
  coa_cd: string
  coa_name: string | null
  has_data: boolean
  level?: number
  term?: string
  biz_line?: string
  value?: number
  m_values?: number[]
  m0?: number[]
  cur_rate?: number
  next_rate?: number
  next_scale_balance?: number
  next_scale_avg?: number
  next_scale_change?: number
  children?: TreeNode[]
}

// 固定列定义：每条 {key, title, width, dataIndex?}
export interface FixedColumn {
  key: string
  title: string
  dataIndex?: string       // 从 record 中取值的字段名（默认 = key）
  width?: number
  render?: (val: any, record: any) => any  // 自定义渲染
}

// M期列定义：[{title, key, width, type: 'money'|'percent'|'raw'}]
export interface MSubColumn {
  title: string
  key: string             // 在 m_values 中对应的子索引（在每期内）
  width?: number
  type?: 'money' | 'percent' | 'raw' | 'bp'
  color?: (v: number) => string  // 自定义颜色
}

// 单期 M 组：{title, columns: MSubColumn[]}  -- 一组 M0/M1/.../M24
export interface MGroup {
  title: string  // 例如 "M0"
  columns: MSubColumn[]
}

interface Props {
  endpoint: string
  title: string
  description?: string
  // 模式 A（兼容旧的 5 个简单接口）：单一固定列编码+名称 + 平铺列头
  columns?: number
  columnHeaders?: string[]
  // 模式 B（新 4 个分组接口）：完全自定义
  fixedColumns?: FixedColumn[]      // 固定列（左侧）
  mGroups?: MGroup[]                 // M0/M1/...分组列头
  mGroupsCount?: number              // 一共有多少组（默认 = mGroups.length）
  // 版本控制
  showVersionSelector?: boolean      // 是否显示版本选择器（默认 true）
  calcVersion?: string                // 当前选中的版本号（受控）
  onCalcVersionChange?: (v: string) => void
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
    if (v == null || v === 0) return '-'
    return v.toFixed(2) + '%'
  },
  bp: (v: number | null | undefined) => {
    if (v == null || v === 0) return '-'
    return (v > 0 ? '+' : '') + v.toFixed(2)
  },
  raw: (v: number | null | undefined) => {
    if (v == null || v === 0) return '-'
    return v.toFixed(4)
  }
}

const decorate = (nodes: any[], depth = 0): any[] =>
  nodes.map(n => {
    const node = {
      ...n,
      key: `rv_${n.id || n.coa_cd}`,
      id: n.id,
      depth
    }
    if (n.children && n.children.length > 0) {
      node.children = decorate(n.children, depth + 1)
    }
    return node
  })

const collectExpandableKeys = (nodes: any[]): React.Key[] => {
  const keys: React.Key[] = []
  const walk = (list: any[]) => {
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

const ResultViewLayout = (props: Props) => {
  const {
    endpoint, title, description,
    columns, columnHeaders,
    fixedColumns, mGroups, mGroupsCount,
    showVersionSelector = true,
    calcVersion,
    onCalcVersionChange,
  } = props

  const isSimpleMode = !!columnHeaders  // 简单模式 = 老5个页面

  const [treeData, setTreeData] = useState<any[]>([])
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>([])
  const [loading, setLoading] = useState(false)
  const [internalVersion, setInternalVersion] = useState<string>('')

  // 受控/非受控版本号
  const version = calcVersion !== undefined ? calcVersion : internalVersion
  const handleVersionChange = (v: string) => {
    if (onCalcVersionChange) {
      onCalcVersionChange(v)
    } else {
      setInternalVersion(v)
    }
  }

  const fetchData = async () => {
    setLoading(true)
    try {
      const params = version ? { calc_version: version } : {}
      const res = await apiClient.get(endpoint, { params })
      const raw = res.data || []
      const decorated = decorate(raw)
      setTreeData(decorated)
      setExpandedKeys(collectExpandableKeys(decorated))
    } catch (e: any) {
      message.error('加载数据失败：' + (e.response?.data?.detail || e.message))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [endpoint, version])

  // ============= 简单模式列 =============
  const simpleColumns: any[] = useMemo(() => {
    if (!isSimpleMode) return []
    return [
      {
        title: '账户册编码', dataIndex: 'coa_cd', key: 'coa_cd', width: 200,
        fixed: 'left' as const, ellipsis: true,
        render: (val: string, record: any) => {
          const isRoot = record.coa_cd === 'ROOT'
          const hasChildren = record.children && record.children.length > 0
          const color = isRoot ? '#722ed1' : '#1890ff'
          const weight = isRoot || hasChildren ? 'bold' : 'normal'
          return <span style={{ fontFamily: 'monospace', whiteSpace: 'nowrap', color, fontWeight: weight }}>{val}</span>
        }
      },
      {
        title: '账户册名称', dataIndex: 'coa_name', key: 'coa_name', width: 240,
        fixed: 'left' as const, ellipsis: true,
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
      ...(columnHeaders || []).map((h, i) => ({
        title: h,
        key: `col_${i}`,
        width: 95,
        align: 'right' as const,
        render: (_: any, record: any) => {
          const v = record.m_values?.[i]
          const isRoot = record.coa_cd === 'ROOT'
          if (isRoot) return <span style={{ color: '#bbb' }}>-</span>
          return v === undefined || v === 0 || !record.has_data
            ? <span style={{ color: '#bbb' }}>-</span>
            : fmt.money(v)
        }
      }))
    ]
  }, [columnHeaders, isSimpleMode])

  // ============= 分组模式列 =============
  const groupedColumns: any[] = useMemo(() => {
    if (isSimpleMode || !fixedColumns || !mGroups) return []

    // 1. 固定列
    const fixed: any[] = fixedColumns.map(fc => {
      const dataIdx = fc.dataIndex || fc.key
      if (fc.render) {
        return {
          title: fc.title,
          key: fc.key,
          dataIndex: dataIdx,
          width: fc.width || 120,
          fixed: 'left' as const,
          ellipsis: true,
          render: fc.render
        }
      }
      return {
        title: fc.title,
        key: fc.key,
        dataIndex: dataIdx,
        width: fc.width || 120,
        fixed: 'left' as const,
        ellipsis: true
      }
    })

    // 2. M 分组列头：每个组有 title + 子列
    const subColsPerGroup = mGroups[0]?.columns?.length || 4
    const totalGroups = mGroupsCount ?? mGroups.length

    const mColumns: any[] = []
    for (let g = 0; g < totalGroups; g++) {
      const groupDef = mGroups[g]
      const children = groupDef.columns.map((sc, j) => {
        const idxInM = sc.key  // 子列的索引（数字 0/1/2/3...）或 key 名
        return {
          title: sc.title,
          key: `${g}_${j}_${sc.key}`,
          width: sc.width || 90,
          align: 'right' as const,
          render: (_: any, record: any) => {
            const v = record.m_values?.[g * subColsPerGroup + (typeof idxInM === 'number' ? idxInM : j)]
            const isRoot = record.coa_cd === 'ROOT'
            if (isRoot) return <span style={{ color: '#bbb' }}>-</span>
            if (v === undefined || v === null) return <span style={{ color: '#bbb' }}>-</span>
            // 类型格式化
            let display = '-'
            const type = sc.type || 'money'
            if (type === 'money') display = fmt.money(v)
            else if (type === 'percent') display = fmt.percent(v)
            else if (type === 'bp') display = fmt.bp(v)
            else display = fmt.raw(v)
            // 0 简化（除百分比外）
            const showAsZero = (v === 0 || !record.has_data) && type !== 'percent' && type !== 'bp'
            const finalDisplay = showAsZero ? '-' : display
            // 自定义颜色
            const color = sc.color ? sc.color(v) : (v === 0 ? '#bbb' : 'inherit')
            return <span style={{ color }}>{finalDisplay}</span>
          }
        }
      })
      if (groupDef.title) {
        mColumns.push({
          title: groupDef.title,
          children
        })
      } else {
        mColumns.push(...children)
      }
    }

    return [...fixed, ...mColumns]
  }, [fixedColumns, mGroups, mGroupsCount, isSimpleMode])

  const tableColumns = isSimpleMode ? simpleColumns : groupedColumns

  const handleExpand = (expanded: boolean, record: any) => {
    setExpandedKeys(prev =>
      expanded ? [...prev, record.key] : prev.filter(k => k !== record.key)
    )
  }

  // 表格宽度估算
  const fixedWidth = isSimpleMode ? 440 : (fixedColumns || []).reduce((s, f) => s + (f.width || 120), 0)
  const subColsPerGroup = isSimpleMode ? 1 : (mGroups?.[0]?.columns?.length || 4)
  const totalGroups = isSimpleMode ? (columns || 24) : (mGroupsCount ?? mGroups?.length ?? 25)
  const avgSubWidth = isSimpleMode ? 95 : (mGroups?.[0]?.columns?.[0]?.width || 90)
  const scrollX = fixedWidth + totalGroups * subColsPerGroup * avgSubWidth

  return (
    <div>
      <h2>结果查看 / {title}</h2>
      <Card style={{ marginBottom: 12 }}>
        <Space wrap>
          {showVersionSelector && (
            <VersionSelector value={version} onChange={handleVersionChange} />
          )}
          <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
          <Button icon={<DownloadOutlined />} onClick={() => message.info('导出功能待实现')}>导出Excel</Button>
          <Tooltip title="展开全部">
            <Button onClick={() => setExpandedKeys(collectExpandableKeys(treeData))}>全部展开</Button>
          </Tooltip>
          <Tooltip title="收起全部">
            <Button onClick={() => setExpandedKeys([])}>全部收起</Button>
          </Tooltip>
          {description && <span style={{ color: '#666', marginLeft: 8 }}>{description}</span>}
        </Space>
      </Card>

      <Card bodyStyle={{ padding: 0 }}>
        <Spin spinning={loading}>
          <Table
            columns={tableColumns}
            dataSource={treeData}
            rowKey="key"
            loading={loading}
            size="small"
            pagination={{ pageSize: 100, showSizeChanger: true, showTotal: (t) => `共 ${t} 条` }}
            scroll={{ x: scrollX, y: 700 }}
            bordered
            expandable={{
              indentSize: 22,
              expandedRowKeys: expandedKeys,
              onExpand: handleExpand,
              showExpandColumn: false
            }}
            rowClassName={(record: any) => {
              if (record.coa_cd === 'ROOT') return 'result-view-row-root'
              if (record.children && record.children.length > 0) return 'result-view-row-parent'
              return 'result-view-row-leaf'
            }}
          />
        </Spin>
      </Card>

      <style>{`
        .result-view-row-root td { background: #f9f0ff !important; }
        .result-view-row-parent td { background: #fafafa !important; font-weight: 500; }
        .result-view-row-leaf td { background: #ffffff; }
      `}</style>
    </div>
  )
}

export default ResultViewLayout