import React, { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, InputNumber, Space, message, Popconfirm, Upload, Select, Row, Col, Divider, Card } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, ReloadOutlined, FolderOutlined, FileTextOutlined, DownloadOutlined, UploadOutlined } from '@ant-design/icons'
import apiClient from '../api/client'

interface TreeNode {
  key: string
  id?: number
  coa_cd: string
  coa_name: string | null
  value: number | null
  has_data: boolean
  averages?: number[]
  balances?: number[]
  weights?: (number | null)[]
  is_self?: boolean
  plan_balance1?: number
  children?: TreeNode[]
}

const ParamPage = ({ defaultTab = '1' }: { defaultTab?: '1' | '2' | '3' | '4' }) => {
  const [rateData, setRateData] = useState<any[]>([])
  const [riskTree, setRiskTree] = useState<TreeNode[]>([])
  const [planTree, setPlanTree] = useState<TreeNode[]>([])
  const [ftpTree, setFtpTree] = useState<TreeNode[]>([])
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'1' | '2' | '3' | '4'>(defaultTab)

  // 通用展开状态
  const [riskExpanded, setRiskExpanded] = useState<React.Key[]>([])
  const [ftpExpanded, setFtpExpanded] = useState<React.Key[]>([])
  const [planExpanded, setPlanExpanded] = useState<React.Key[]>([])

  // 弹窗
  const [modalVisible, setModalVisible] = useState(false)
  const [modalType, setModalType] = useState<'rate' | 'risk' | 'plan' | 'ftp'>('rate')
  const [editingItem, setEditingItem] = useState<any>(null)
  const [form] = Form.useForm()

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
      key: `coa_${n.id}`,
      id: n.id,
      coa_cd: n.coa_cd,
      coa_name: n.coa_name,
      value: n.value,
      has_data: n.has_data,
      // 透传 24 期字段（业务计划 / 风险权重 / 定价策略）
      balances: n.balances,
      averages: n.averages,
      weights: n.weights,
      preview_values: n.preview_values,
      last_update: n.last_update,
      remark: n.remark,
      is_self: n.is_self,
      children: n.children ? convertKeys(n.children) : undefined
    }))

  const fetchRate = async () => {
    setLoading(true)
    try {
      const res = await apiClient.get('/param/rate-scenario')
      setRateData(Array.isArray(res.data) ? res.data : [])
    } catch (e) { message.error('加载利率情景失败') }
    finally { setLoading(false) }
  }

  const fetchRiskTree = async () => {
    setLoading(true)
    try {
      const res = await apiClient.get('/param/risk-weight/tree')
      const data = Array.isArray(res.data) ? res.data : []
      const converted = convertKeys(data)
      setRiskTree(converted)
      setRiskExpanded(collectAllKeys(converted))
    } catch (e) { message.error('加载风险权重失败') }
    finally { setLoading(false) }
  }

  const fetchFtpTree = async () => {
    setLoading(true)
    try {
      const res = await apiClient.get('/param/ftp-margin/tree')
      const data = Array.isArray(res.data) ? res.data : []
      const converted = convertKeys(data)
      setFtpTree(converted)
      setFtpExpanded(collectAllKeys(converted))
    } catch (e) { message.error('加载FTP利差失败') }
    finally { setLoading(false) }
  }

  const fetchPlanTree = async () => {
    setLoading(true)
    try {
      const res = await apiClient.get('/param/business-plan/tree')
      const data = Array.isArray(res.data) ? res.data : []
      const converted = convertKeys(data)
      setPlanTree(converted)
      setPlanExpanded(collectAllKeys(converted))
    } catch (e) { message.error('加载业务计划失败') }
    finally { setLoading(false) }
  }

  useEffect(() => {
    // 按需加载：仅加载当前 Tab 的数据
    if (activeTab === '1') fetchRate()
    else if (activeTab === '2') fetchRiskTree()
    else if (activeTab === '3') fetchFtpTree()
    else if (activeTab === '4') fetchPlanTree()
  }, [activeTab])

  const handleAdd = (type: 'rate' | 'risk' | 'plan' | 'ftp') => {
    setModalType(type)
    setEditingItem(null)
    form.resetFields()
    if (type === 'rate') {
      // 利率情景新增时，调整值默认为 0（即M1~M24 = 当前值）
      form.setFieldsValue({ scenario_shift: 0 })
    }
    setModalVisible(true)
  }

  const handleEdit = async (type: 'rate' | 'risk' | 'plan' | 'ftp', item: any) => {
    setModalType(type)
    setEditingItem(item)
    form.resetFields()
    if (type === 'plan') {
      // 业务计划：先加载24期明细到表单
      try {
        const res = await apiClient.get(`/param/business-plan/${item.coa_cd}`)
        const detail = res.data
        const values: any = {
          coa_lvl: detail.coa_lvl || '',
          coa_cd: detail.coa_cd,
          coa_name: detail.coa_name || ''
        }
        for (let i = 1; i <= 24; i++) {
          values[`average_${i}`] = detail.averages?.[i-1]
          values[`balance_${i}`] = detail.balances?.[i-1]
        }
        form.setFieldsValue(values)
      } catch (e) {
        // 没有24期明细时只用基本信息
        form.setFieldsValue({ coa_lvl: '', coa_cd: item.coa_cd, coa_name: item.coa_name })
        for (let i = 1; i <= 24; i++) {
          form.setFieldsValue({ [`average_${i}`]: item.averages?.[i-1], [`balance_${i}`]: item.plan_balance1 && i === 1 ? item.plan_balance1 : null })
        }
      }
    } else if (type === 'risk') {
      // 风险权重：先加载24期明细
      try {
        const res = await apiClient.get(`/param/risk-weight/${item.coa_cd}`)
        const detail = res.data
        const values: any = {
          coa_cd: detail.coa_cd,
          coa_name: detail.coa_name || ''
        }
        for (let i = 1; i <= 24; i++) {
          values[`risk_weight_${i}`] = detail.weights?.[i-1]
        }
        form.setFieldsValue(values)
      } catch (e) {
        form.setFieldsValue({ coa_cd: item.coa_cd, coa_name: item.coa_name })
        for (let i = 1; i <= 24; i++) {
          form.setFieldsValue({ [`risk_weight_${i}`]: item.weights?.[i-1] })
        }
      }
    } else {
      form.setFieldsValue(item)
      if (type === 'rate' && (item.scenario_shift === null || item.scenario_shift === undefined)) {
        form.setFieldsValue({ scenario_shift: 0 })
      }
    }
    setModalVisible(true)
  }

  const handleDelete = async (type: 'rate' | 'risk' | 'plan' | 'ftp', id: number) => {
    try {
      const endpoint = type === 'rate' ? 'rate-scenario' : type === 'risk' ? 'risk-weight' : type === 'plan' ? 'business-plan' : 'ftp-margin'
      await apiClient.delete(`/param/${endpoint}/${id}`)
      message.success('删除成功')
      if (type === 'risk') fetchRiskTree()
      else if (type === 'ftp') fetchFtpTree()
      else if (type === 'plan') fetchPlanTree()
      else fetchRate()
    } catch (e) { message.error('删除失败') }
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      // 利率情景用普通POST/PUT
      if (modalType === 'rate') {
        const endpoint = 'rate-scenario'
        if (editingItem?.id) {
          await apiClient.put(`/param/${endpoint}/${editingItem.id}`, values)
        } else {
          await apiClient.post(`/param/${endpoint}`, values)
        }
        message.success(editingItem ? '更新成功' : '创建成功')
        fetchRate()
      } else {
        // 风险权重/FTP利差/业务计划：用 /save 接口（upsert）
        const endpoint = modalType === 'risk' ? 'risk-weight' : modalType === 'plan' ? 'business-plan' : 'ftp-margin'
        await apiClient.post(`/param/${endpoint}/save`, values)
        message.success(editingItem?.id ? '更新成功' : '创建成功')
        if (modalType === 'risk') fetchRiskTree()
        else if (modalType === 'ftp') fetchFtpTree()
        else if (modalType === 'plan') fetchPlanTree()
      }
      setModalVisible(false)
    } catch (e: any) {
      message.error('操作失败: ' + (e.response?.data?.detail || e.message))
    }
  }

  // 通用导入导出
  const handleExport = async (type: string) => {
    try {
      const res = await apiClient.get(`/param/${type}/export`, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `${type}.xlsx`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
      message.success('导出成功')
    } catch (e: any) {
      message.error('导出失败: ' + (e.response?.data?.detail || e.message))
    }
  }

  const handleImport = async (type: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    try {
      const res = await apiClient.post(`/param/${type}/import`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      message.success(`导入成功: 新增 ${res.data.inserted} 条, 更新 ${res.data.updated} 条`)
      if (type === 'risk-weight') fetchRiskTree()
      else if (type === 'ftp-margin') fetchFtpTree()
      else if (type === 'business-plan') fetchPlanTree()
      else fetchRate()
    } catch (e: any) {
      message.error('导入失败: ' + (e.response?.data?.detail || e.message))
    }
    return false
  }

  const ImportBtn = ({ type }: { type: string }) => (
    <Upload beforeUpload={(f) => handleImport(type, f)} showUploadList={false} accept=".xlsx,.xls">
      <Button icon={<UploadOutlined />}>导入Excel</Button>
    </Upload>
  )

  // ===== 利率情景列 =====
  const fmtRate = (v: number | null) => v != null ? (Number(v) * 100).toFixed(2) + '%' : '-'
  const rateBaseColumns = [
    { title: '序号', dataIndex: 'order_number', key: 'order_number', width: 70, fixed: 'left' as const },
    { title: '曲线名称', dataIndex: 'curve_name', key: 'curve_name', width: 180, ellipsis: true, fixed: 'left' as const },
    { title: '曲线ID', dataIndex: 'curve_id', key: 'curve_id', width: 80, fixed: 'left' as const },
    {
      title: '当前值', dataIndex: 'current_curve_value', key: 'current_curve_value', width: 90,
      render: fmtRate, fixed: 'left' as const
    },
    {
      title: '调整值', dataIndex: 'scenario_shift', key: 'scenario_shift', width: 90,
      render: (v: number) => v != null ? (Number(v) * 10000).toFixed(0) + ' BP' : '-',
      fixed: 'left' as const
    },
  ]
  const rateMColumns = Array.from({ length: 24 }, (_, i) => ({
    title: 'M' + (i + 1),
    dataIndex: 'm' + (i + 1) + '_value',
    key: 'm' + (i + 1) + '_value',
    width: 75,
    render: fmtRate
  }))
  const rateColumns = [
    ...rateBaseColumns,
    ...rateMColumns,
    {
      title: '操作', key: 'action', width: 120, fixed: 'right' as const,
      render: (_: any, r: any) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => handleEdit('rate', r)} />
          <Popconfirm title="确认删除?" onConfirm={() => handleDelete('rate', r.id)}>
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      )
    }
  ]

  // ===== 风险权重/FTP/业务计划树形列 =====
  const buildTreeColumns = (valueTitle: string, valueFormatter: (v: number | null) => string) => [
    {
      title: '账户册编码', dataIndex: 'coa_cd', key: 'coa_cd', width: 160, fixed: 'left' as const, ellipsis: true,
      render: (val: string) => <span style={{ fontFamily: 'monospace', whiteSpace: 'nowrap' }}>{val}</span>
    },
    {
      title: '账户册名称', dataIndex: 'coa_name', key: 'coa_name', width: 200, fixed: 'left' as const, ellipsis: true,
      render: (val: string, record: TreeNode) => (
        <Space>
          {record.has_data ? <FileTextOutlined style={{ color: '#1890ff' }} /> : <FolderOutlined style={{ color: '#999' }} />}
          <span style={{ color: record.has_data ? 'inherit' : '#999', whiteSpace: 'nowrap' }}>{val || '-'}</span>
        </Space>
      )
    },
    {
      title: valueTitle, dataIndex: 'value', key: 'value', width: 160, align: 'right' as const,
      render: (val: number | null, record: TreeNode) => (
        <span style={{ color: record.has_data ? 'inherit' : '#bbb' }}>
          {record.has_data && val !== null ? valueFormatter(val) : '-'}
        </span>
      )
    },
    {
      title: '操作', key: 'action', width: 120, fixed: 'right' as const,
      render: (_: any, record: TreeNode) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => handleEdit(activeTab === '2' ? 'risk' : activeTab === '3' ? 'ftp' : 'plan', record)}>
            {record.has_data ? '编辑24期' : '新增'}
          </Button>
        </Space>
      )
    }
  ]

  // ===== 业务计划展开行 - 24期日均增量明细 =====
  const renderPlanExpand = (record: TreeNode) => {
    const avgs = record.averages || new Array(24).fill(0)
    const rows = [
      { label: 'M1~M6 上半年', indices: [0,1,2,3,4,5] },
      { label: 'M7~M12 下半年', indices: [6,7,8,9,10,11] },
      { label: 'M13~M18 次年上半年', indices: [12,13,14,15,16,17] },
      { label: 'M19~M24 次年下半年', indices: [18,19,20,21,22,23] }
    ]
    return (
      <div style={{ padding: '8px 24px', background: '#fafafa' }}>
        <Row gutter={[8, 8]}>
          {rows.map(r => (
            <React.Fragment key={r.label}>
              <Col span={3} style={{ color: '#666', fontSize: 12, lineHeight: '32px' }}>{r.label}</Col>
              {r.indices.map(i => (
                <Col span={3} key={i}>
                  <div style={{ fontSize: 11, color: '#999' }}>M{i+1}</div>
                  <div style={{ color: avgs[i] ? '#1890ff' : '#bbb' }}>
                    {avgs[i] !== undefined ? fmtMoney(avgs[i]) : '-'}
                  </div>
                </Col>
              ))}
            </React.Fragment>
          ))}
        </Row>
      </div>
    )
  }

  // ===== 业务计划专属列：基础信息 + 24×2（规模增量/日均增量）+ 操作 =====
  const buildPlanColumns = () => {
    const cols: any[] = [
      {
        title: '账户册编码', dataIndex: 'coa_cd', key: 'coa_cd',
        width: 200, fixed: 'left' as const, ellipsis: true,
        render: (val: string) => <span style={{ fontFamily: 'monospace', whiteSpace: 'nowrap' }}>{val}</span>
      },
      {
        title: '账户册名称', dataIndex: 'coa_name', key: 'coa_name',
        width: 260, fixed: 'left' as const, ellipsis: true,
        render: (val: string, record: TreeNode) => (
          <Space>
            {record.has_data ? <FileTextOutlined style={{ color: '#1890ff' }} /> : <FolderOutlined style={{ color: '#999' }} />}
            <span style={{ color: record.has_data ? 'inherit' : '#999', whiteSpace: 'nowrap' }}>{val || '-'}</span>
          </Space>
        )
      }
    ]
    // M1~M24 × 2 列（规模增量 + 日均增量），相邻成对
    for (let i = 1; i <= 24; i++) {
      // 规模增量列
      cols.push({
        title: `${i}规模增量`,
        key: `bal_${i}`,
        width: 80,
        align: 'right' as const,
        render: (_: any, record: TreeNode) => {
          const bals = record.balances || []
          const avgs = record.averages || []
          const v = bals[i - 1] || 0
          const av = avgs[i - 1] || 0
          // 互斥显示：如果日均增量有值且规模增量为0，则表示用日均那侧（不属于这里）
          if (!record.has_data) return <span style={{ color: '#bbb' }}>-</span>
          if (!v) return <span style={{ color: '#bbb' }}>-</span>
          return <span style={{ color: v > 0 ? '#1890ff' : '#cf1322' }}>{fmtMoney(v)}</span>
        }
      })
      // 日均增量列
      cols.push({
        title: `${i}日均增量`,
        key: `avg_${i}`,
        width: 80,
        align: 'right' as const,
        render: (_: any, record: TreeNode) => {
          const avgs = record.averages || []
          const bals = record.balances || []
          const v = avgs[i - 1] || 0
          if (!record.has_data) return <span style={{ color: '#bbb' }}>-</span>
          if (!v) return <span style={{ color: '#bbb' }}>-</span>
          return <span style={{ color: v > 0 ? '#1890ff' : '#cf1322' }}>{fmtMoney(v)}</span>
        }
      })
    }
    // 操作列固定右侧
    cols.push({
      title: '操作', key: 'action', width: 130, fixed: 'right' as const,
      render: (_: any, record: TreeNode) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => handleEdit('plan', record)}>
            {record.has_data ? '编辑24期' : '新增'}
          </Button>
        </Space>
      )
    })
    return cols
  }

  // ===== 风险权重专属列：基础信息 + 24期风险权重（不汇总，支持继承）=====
  const buildRiskColumns = () => {
    const cols: any[] = [
      {
        title: '账户册编码', dataIndex: 'coa_cd', key: 'coa_cd',
        width: 200, fixed: 'left' as const, ellipsis: true,
        render: (val: string) => <span style={{ fontFamily: 'monospace', whiteSpace: 'nowrap' }}>{val}</span>
      },
      {
        title: '账户册名称', dataIndex: 'coa_name', key: 'coa_name',
        width: 260, fixed: 'left' as const, ellipsis: true,
        render: (val: string, record: TreeNode) => (
          <Space>
            {record.has_data
              ? <FileTextOutlined style={{ color: record.is_self ? '#1890ff' : '#52c41a' }} />
              : <FolderOutlined style={{ color: '#999' }} />}
            <span style={{ color: record.has_data ? 'inherit' : '#999', whiteSpace: 'nowrap' }}>{val || '-'}</span>
            {record.has_data && !record.is_self && (
              <span style={{ color: '#52c41a', fontSize: 11, padding: '0 4px', background: '#f6ffed', border: '1px solid #b7eb8f', borderRadius: 2 }}>继承</span>
            )}
          </Space>
        )
      }
    ]
    // M1~M24 列
    for (let i = 1; i <= 24; i++) {
      cols.push({
        title: `M${i}`,
        key: `risk_${i}`,
        width: 75,
        align: 'right' as const,
        render: (_: any, record: TreeNode) => {
          const ws = record.weights || []
          const v = ws[i - 1]
          if (v === null || v === undefined) return <span style={{ color: '#bbb' }}>-</span>
          // 继承显示淡颜色，自配置显示蓝色
          const color = record.is_self ? '#1890ff' : '#52c41a'
          return <span style={{ color }}>{(v * 100).toFixed(2)}%</span>
        }
      })
    }
    cols.push({
      title: '操作', key: 'action', width: 130, fixed: 'right' as const,
      render: (_: any, record: TreeNode) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => handleEdit('risk', record)}>
            {record.is_self ? '编辑24期' : '编辑覆盖'}
          </Button>
        </Space>
      )
    })
    return cols
  }

  const fmtPercent = (v: number) => (v * 100).toFixed(2) + '%'
  const fmtMoney = (v: number) => {
    if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(2) + ' 亿'
    if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(2) + ' 万'
    return v.toFixed(2)
  }

  const items = [
    {
      key: '1',
      label: `利率情景 (${rateData.length})`,
      children: (
        <div>
          <Space style={{ marginBottom: 16 }}>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => handleAdd('rate')}>新增</Button>
            <Button icon={<ReloadOutlined />} onClick={fetchRate}>刷新</Button>
            <Button icon={<DownloadOutlined />} onClick={() => handleExport('rate-scenario')}>导出Excel</Button>
            <ImportBtn type="rate-scenario" />
          </Space>
          <Table
            columns={rateColumns}
            dataSource={rateData}
            rowKey="id"
            loading={loading}
            size="small"
            scroll={{ x: 2400 }}
            pagination={{ pageSize: 20, showSizeChanger: true }}
            bordered
          />
        </div>
      )
    },
    {
      key: '2',
      label: `风险权重 (${riskTree.length})`,
      children: (
        <div>
          <Space style={{ marginBottom: 16 }} wrap>
            <Button icon={<ReloadOutlined />} onClick={fetchRiskTree}>刷新</Button>
            <Button icon={<DownloadOutlined />} onClick={() => handleExport('risk-weight')}>导出Excel</Button>
            <ImportBtn type="risk-weight" />
            <span style={{ color: '#666' }}>
              横向滚动查看 M1~M24 风险权重；父级配置后下级继承（绿色"继承"标签），点击"编辑覆盖"为当前节点单独设置
            </span>
          </Space>
          <Table
            columns={buildRiskColumns()}
            dataSource={riskTree}
            rowKey="key"
            loading={loading}
            size="small"
            pagination={false}
            scroll={{ x: 2680, y: 600 }}
            bordered
            expandable={{
              indentSize: 20,
              expandedRowKeys: riskExpanded,
              onExpand: (expanded, record) => {
                setRiskExpanded(prev =>
                  expanded ? [...prev, record.key] : prev.filter(k => k !== record.key)
                )
              }
            }}
          />
        </div>
      )
    },
    {
      key: '3',
      label: `FTP利差 (${ftpTree.length})`,
      children: (
        <div>
          <Space style={{ marginBottom: 16 }}>
            <Button icon={<ReloadOutlined />} onClick={fetchFtpTree}>刷新</Button>
            <Button icon={<DownloadOutlined />} onClick={() => handleExport('ftp-margin')}>导出Excel</Button>
            <ImportBtn type="ftp-margin" />
          </Space>
          <Table
            columns={buildTreeColumns('FTP利差', fmtPercent)}
            dataSource={ftpTree}
            rowKey="key"
            loading={loading}
            size="small"
            pagination={false}
            scroll={{ x: 880, y: 600 }}
            bordered
            expandable={{
              indentSize: 20,
              expandedRowKeys: ftpExpanded,
              onExpand: (expanded, record) => {
                setFtpExpanded(prev =>
                  expanded ? [...prev, record.key] : prev.filter(k => k !== record.key)
                )
              }
            }}
          />
        </div>
      )
    },
    {
      key: '4',
      label: `业务计划 (${planTree.length})`,
      children: (
        <div>
          <Space style={{ marginBottom: 16 }} wrap>
            <Button icon={<ReloadOutlined />} onClick={fetchPlanTree}>刷新</Button>
            <Button icon={<DownloadOutlined />} onClick={() => handleExport('business-plan')}>导出Excel</Button>
            <ImportBtn type="business-plan" />
            <span style={{ color: '#666' }}>每个 M 含"规模增量"+"日均增量"两列，二选一互斥；点击"编辑24期"配置</span>
          </Space>
          <Table
            columns={buildPlanColumns()}
            dataSource={planTree}
            rowKey="key"
            loading={loading}
            size="small"
            pagination={false}
            scroll={{ x: 4680, y: 600 }}
            bordered
            defaultExpandAllRows
          />
        </div>
      )
    }
  ]

  const renderForm = () => {
    if (modalType === 'rate') {
      return (
        <>
          <Form.Item name="order_number" label="序号">
            <InputNumber style={{ width: '100%' }} min={1} />
          </Form.Item>
          <Form.Item name="curve_name" label="曲线名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="curve_id" label="曲线ID">
            <Input />
          </Form.Item>
          <Form.Item name="current_curve_value" label="当前值" rules={[{ required: true }]}>
            <InputNumber style={{ width: '100%' }} step={0.0001} placeholder="小数，如0.0325" />
          </Form.Item>
          <Form.Item
            name="scenario_shift"
            label="调整值(BP)"
            extra="输入调整值（如300表示上行300BP），保存时自动用 [当前值 + 调整值/10000] 计算所有M列"
          >
            <InputNumber style={{ width: '100%' }} step={1} placeholder="如 300 / -100 / 0" />
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={2} />
          </Form.Item>
        </>
      )
    } else if (modalType === 'risk') {
      // 风险权重：24 期 risk_weight_1~24（不汇总，支持继承覆盖）
      return (
        <>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="coa_cd" label="账户册编码" rules={[{ required: true }]}>
                <Input disabled style={{ color: '#999' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="coa_name" label="账户册名称">
                <Input disabled style={{ color: '#999' }} />
              </Form.Item>
            </Col>
          </Row>
          <Divider orientation="left" style={{ color: '#1890ff', fontWeight: 'bold' }}>
            未来24个月风险权重（小数，如 0.1 表示 10%）
          </Divider>
          <div style={{ color: '#999', marginBottom: 12, fontSize: 12 }}>
            配置每个月的风险权重。本节点未配置的字段会从最近的祖先节点继承。
          </div>
          <Row gutter={[12, 8]}>
            {Array.from({ length: 24 }, (_, i) => i + 1).map(i => (
              <Col span={4} key={`rw_${i}`}>
                <Form.Item
                  name={`risk_weight_${i}`}
                  label={`M${i}`}
                  style={{ marginBottom: 8 }}
                >
                  <InputNumber
                    style={{ width: '100%' }}
                    step={0.01}
                    min={0}
                    max={1.5}
                    placeholder="0.10"
                  />
                </Form.Item>
              </Col>
            ))}
          </Row>
        </>
      )
    } else if (modalType === 'plan') {
      // 业务计划：24期（规模增量 + 日均增量），每对互斥，只能填一个
      const months = Array.from({ length: 24 }, (_, i) => i + 1)
      const fmtNum = (v: any) => v !== null && v !== undefined && v !== '' ? `${Number(v).toLocaleString()}` : ''
      const parseNum = (v: any) => v !== null && v !== undefined && v !== '' ? Number(String(v).replace(/,/g, '')) : null
      // 互斥：填一个时清空另一个（不弹错）
      const handleExclusiveChange = (i: number, type: 'bal' | 'avg') => (val: any) => {
        if (val !== null && val !== undefined && val !== '') {
          const other = type === 'bal' ? `average_${i}` : `balance_${i}`
          form.setFieldsValue({ [other]: null })
        }
      }
      // 通过 Form.Item 的 dependencies + getFieldValue 动态判断是否禁用
      return (
        <>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="coa_lvl" label="层级">
                <Input disabled style={{ color: '#999' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="coa_cd" label="账户册编码" rules={[{ required: true }]}>
                <Input disabled style={{ color: '#999' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="coa_name" label="账户册名称">
                <Input disabled style={{ color: '#999' }} />
              </Form.Item>
            </Col>
          </Row>
          <Divider orientation="left" style={{ color: '#1890ff', fontWeight: 'bold' }}>
            未来24个月业务计划（规模增量 / 日均增量，二选一互斥）
          </Divider>
          <div style={{ color: '#999', marginBottom: 12, fontSize: 12 }}>
            每对同 M 的两个字段互斥，只能填一个（填一个时另一个自动清空）。正数代表增加，负数代表减少。
          </div>
          <Row gutter={[8, 8]}>
            {months.map(i => (
              <Col span={12} key={`pair_${i}`}>
                <Row gutter={4}>
                  <Col span={1} style={{ lineHeight: '32px', textAlign: 'center', color: '#1890ff', fontWeight: 'bold' }}>
                    M{i}
                  </Col>
                  <Col span={11}>
                    <Form.Item
                      name={`balance_${i}`}
                      label={<span style={{ fontSize: 11, color: '#999' }}>规模增量</span>}
                      style={{ marginBottom: 8 }}
                      dependencies={[`average_${i}`]}
                    >
                      <InputNumber
                        style={{ width: '100%' }}
                        step={1000000}
                        formatter={fmtNum}
                        parser={parseNum}
                        placeholder="规模增量(元)"
                        onChange={handleExclusiveChange(i, 'bal')}
                      />
                    </Form.Item>
                  </Col>
                  <Col span={11}>
                    <Form.Item
                      name={`average_${i}`}
                      label={<span style={{ fontSize: 11, color: '#999' }}>日均增量</span>}
                      style={{ marginBottom: 8 }}
                      dependencies={[`balance_${i}`]}
                    >
                      <InputNumber
                        style={{ width: '100%' }}
                        step={1000000}
                        formatter={fmtNum}
                        parser={parseNum}
                        placeholder="日均增量(元)"
                        onChange={handleExclusiveChange(i, 'avg')}
                      />
                    </Form.Item>
                  </Col>
                </Row>
              </Col>
            ))}
          </Row>
          <Divider style={{ marginTop: 8 }} />
          <div style={{ color: '#999', fontSize: 12 }}>
            💡 填写示例：第 3 个月预计增加存款 1000 万，则在 M3 规模增量 填 10000000；日均增量留空。
          </div>
        </>
      )
    } else {
      return (
        <>
          <Form.Item name="coa_cd" label="账户册编码">
            <Input />
          </Form.Item>
          <Form.Item name="spread" label="FTP利差">
            <InputNumber style={{ width: '100%' }} step={0.001} />
          </Form.Item>
        </>
      )
    }
  }

  // 当前激活 Tab 的标题（用于页面 h2）
  const tabTitles: Record<string, string> = {
    '1': '利率情景',
    '2': '风险权重',
    '3': 'FTP利差',
    '4': '业务计划'
  }

  // 当前激活 Tab 对应的内容（而非 Tab 切换）
  const currentTab = items.find(i => i.key === activeTab)

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>{tabTitles[activeTab]}（参数配置）</h2>
      <Card bordered={false} style={{ background: 'transparent' }}>
        {currentTab?.children}
      </Card>

      <Modal
        title={editingItem ? `编辑 - ${editingItem.coa_name || editingItem.coa_cd || ''}` : '新增'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        destroyOnClose
        width={modalType === 'plan' ? 1100 : 600}
      >
        <Form form={form} layout="vertical">
          {renderForm()}
        </Form>
      </Modal>
    </div>
  )
}

export default ParamPage