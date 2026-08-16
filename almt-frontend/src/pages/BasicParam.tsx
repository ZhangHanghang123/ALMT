import { useState, useEffect } from 'react'
import { Card, Table, Tabs, Button, Modal, Form, Input, InputNumber, Space, message, Popconfirm, DatePicker, Select } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, ReloadOutlined, ClockCircleOutlined, ProfileOutlined, FileSearchOutlined, FolderOutlined, FileTextOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import apiClient from '../api/client'

// ===== 账户册属性 字典配置 =====
const TERM_OPTIONS = ['1D', '7D', '1M', '3M', '6M', '9M', '1Y', '2Y', '3Y', '5Y', '10Y', '15Y', '20Y', '30Y']
const ACCRULE_OPTIONS = ['Actual/360', 'Actual/365', '30/360', 'Actual/Actual']
const BUSINESS_LINE_OPTIONS = ['计财部', '金融市场部', '投资银行部', '个人金融部', '公司金融部', '小微金融部', '数字金融部', '交易银行部']
const REPLACE_TYPE_OPTIONS = ['固定利率', '浮动利率', '混合利率']
const REPRICE_FREQ_OPTIONS = ['1D', '7D', '1M', '3M', '6M', '1Y']

// ===== 报表口径 23个指标（参考报表口径.xlsx列名） =====
const CALIBER_INDICATORS = [
  { name: '利息净收入', key: 1 },
  { name: '存贷比', key: 2 },
  { name: '存款付息率', key: 3 },
  { name: '贷款收息率', key: 4 },
  { name: '投资收息率', key: 5 },
  { name: '生息资产收息率', key: 6 },
  { name: '净息差', key: 7 },
  { name: '付息负债付息率', key: 8 },
  { name: '广义信贷规模', key: 9 },
  { name: '资本充足率', key: 10 },
  { name: '90天缺口率', key: 11 },
  { name: '流动性比例', key: 12 },
  { name: '流动性覆盖率', key: 13 },
  { name: '净稳定资金比例(<6月)', key: 14 },
  { name: '净稳定资金比例(6-12月)', key: 15 },
  { name: '净稳定资金比例(>=1年)', key: 16 },
  { name: '同业负债比例', key: 17 },
  { name: '核心负债比例', key: 18 },
  { name: '未来余额', key: 19 },
  { name: '备用1', key: 20 },
  { name: '备用2', key: 21 },
  { name: '备用3', key: 22 },
  { name: '备用4', key: 23 }
]

// ===== 报表口径 取数类型字典 =====
const CALIBER_TYPE_OPTIONS = [
  { value: 'NII', label: 'NII - 净利息收入' },
  { value: 'RWA', label: 'RWA - 风险加权资产' },
  { value: 'B', label: 'B - 余额' },
  { value: 'AB', label: 'AB - 日均余额' },
  { value: 'CF1', label: 'CF1 - 1个月内现金流' },
  { value: 'CF3', label: 'CF3 - 3个月内现金流' },
  { value: 'CF1-6', label: 'CF1-6 - 1-6个月现金流' },
  { value: 'CF7-12', label: 'CF7-12 - 7-12个月现金流' },
  { value: 'CF12+', label: 'CF12+ - 12个月以上现金流' },
  { value: 'B-CF3', label: 'B-CF3 - 余额-3月内现金流' }
]

const BasicParamPage = () => {
  const [timeStep, setTimeStep] = useState<any[]>([])
  const [attrTree, setAttrTree] = useState<any[]>([])
  const [caliber, setCaliber] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('1')

  // 收益率曲线列表（来自利率情景）
  const [curveOptions, setCurveOptions] = useState<{ value: string; label: string }[]>([])

  // 账户册下拉选项（供报表口径使用）
  const [coaOptions, setCoaOptions] = useState<{ value: string; label: string }[]>([])

  // 报表口径字典：分子/分母
  const [numDictOptions, setNumDictOptions] = useState<{ value: string; label: string }[]>([])
  const [denDictOptions, setDenDictOptions] = useState<{ value: string; label: string }[]>([])

  // 展开状态
  const [attrExpanded, setAttrExpanded] = useState<React.Key[]>([])

  // 弹窗
  const [modalVisible, setModalVisible] = useState(false)
  const [modalType, setModalType] = useState<'time' | 'attr' | 'caliber'>('time')
  const [editingItem, setEditingItem] = useState<any>(null)
  const [form] = Form.useForm()

  // 搜索
  const [search, setSearch] = useState('')

  // 时间步选择的年月
  const [stepYear, setStepYear] = useState<number>(dayjs().year())
  const [stepMonth, setStepMonth] = useState<number>(dayjs().month() + 1)

  const collectAllKeys = (nodes: any[]): React.Key[] => {
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

  const convertKeys = (nodes: any[]) =>
    nodes.map(n => ({
      ...n,
      key: `attr_${n.id}`,
      children: n.children ? convertKeys(n.children) : undefined
    }))

  const fetchTimeStep = async () => {
    setLoading(true)
    try {
      const res = await apiClient.get('/basic-param/time-step')
      setTimeStep(Array.isArray(res.data) ? res.data : [])
    } catch (e) { message.error('加载时间步失败') }
    finally { setLoading(false) }
  }

  const fetchAttrTree = async () => {
    setLoading(true)
    try {
      const res = await apiClient.get('/basic-param/coa-attribute/tree')
      const data = Array.isArray(res.data) ? res.data : []
      const converted = convertKeys(data)
      setAttrTree(converted)
      setAttrExpanded(collectAllKeys(converted))
    } catch (e) { message.error('加载账户册属性失败') }
    finally { setLoading(false) }
  }

  const fetchCaliber = async () => {
    setLoading(true)
    try {
      const res = await apiClient.get('/basic-param/metric-caliber', { params: { skip: 0, limit: 1000 } })
      setCaliber(Array.isArray(res.data) ? res.data : [])
    } catch (e) { message.error('加载报表口径失败') }
    finally { setLoading(false) }
  }

  // 加载利率情景中的曲线列表
  const fetchCurveOptions = async () => {
    try {
      const res = await apiClient.get('/param/rate-scenario', { params: { skip: 0, limit: 1000 } })
      const data = Array.isArray(res.data) ? res.data : []
      // 去重，按 curve_id 分组
      const map = new Map<string, string>()
      data.forEach((d: any) => {
        if (d.curve_id && !map.has(String(d.curve_id))) {
          map.set(String(d.curve_id), d.curve_name || `曲线${d.curve_id}`)
        }
      })
      const options = Array.from(map.entries()).map(([id, name]) => ({
        value: id,
        label: `${id} - ${name}`
      }))
      setCurveOptions(options)
    } catch (e) {
      console.error('加载曲线列表失败', e)
    }
  }

  // 监听曲线变化，自动带出曲线名称
  const handleCurveIdChange = (value: string) => {
    const option = curveOptions.find(o => o.value === value)
    if (option) {
      // label 格式: "id - name"
      const name = option.label.split(' - ').slice(1).join(' - ')
      form.setFieldsValue({ curve_name: name })
    }
  }

  useEffect(() => {
    fetchTimeStep()
    fetchAttrTree()
    fetchCaliber()
    fetchCurveOptions()
    fetchCoaOptions()
    fetchDictValues()
  }, [])

  // 加载分子/分母字典
  const fetchDictValues = async () => {
    try {
      const [numRes, denRes] = await Promise.all([
        apiClient.get('/basic-param/dict/NUM/values'),
        apiClient.get('/basic-param/dict/DEN/values')
      ])
      setNumDictOptions((numRes.data || []).map((d: any) => ({ value: d.value_code, label: `${d.value_code} - ${d.value_name}` })))
      setDenDictOptions((denRes.data || []).map((d: any) => ({ value: d.value_code, label: `${d.value_code} - ${d.value_name}` })))
    } catch (e) {
      console.error('加载字典失败', e)
    }
  }

  // 加载账户册下拉选项
  const fetchCoaOptions = async () => {
    try {
      const res = await apiClient.get('/basic-param/coa-options')
      setCoaOptions(Array.isArray(res.data) ? res.data : [])
    } catch (e) {
      console.error('加载账户册选项失败', e)
    }
  }

  // 报表口径：选择 coa_cd 后自动带出 coa_name
  const handleCaliberCoaChange = (value: string) => {
    const opt = coaOptions.find(o => o.value === value)
    if (opt) {
      // label 格式: "code - name"
      const name = opt.label.split(' - ').slice(1).join(' - ')
      form.setFieldsValue({ coa_name: name })
    }
  }

  const handleAdd = (type: 'time' | 'attr' | 'caliber') => {
    setModalType(type)
    setEditingItem(null)
    form.resetFields()
    setModalVisible(true)
  }

  const handleEdit = (type: 'time' | 'attr' | 'caliber', item: any) => {
    setModalType(type)
    setEditingItem(item)
    const values = { ...item }
    if (values.month_end_date) values.month_end_date = dayjs(values.month_end_date)
    form.setFieldsValue(values)
    setModalVisible(true)
  }

  const handleDelete = async (type: string, id: number) => {
    try {
      const endpoint = type === 'time' ? 'time-step' : type === 'attr' ? 'coa-attribute' : 'metric-caliber'
      await apiClient.delete(`/basic-param/${endpoint}/${id}`)
      message.success('删除成功')
      if (type === 'time') fetchTimeStep()
      else if (type === 'attr') fetchAttrTree()
      else fetchCaliber()
    } catch (e) { message.error('删除失败') }
  }

  const handleRegenerateTimeStep = async () => {
    try {
      const res = await apiClient.post('/basic-param/time-step/regenerate', {
        year: stepYear,
        start_month: stepMonth
      })
      message.success(res.data.message || '时间步已重新生成')
      fetchTimeStep()
    } catch (e: any) {
      message.error('生成失败: ' + (e.response?.data?.detail || e.message))
    }
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (values.month_end_date && dayjs.isDayjs(values.month_end_date)) {
        values.month_end_date = values.month_end_date.format('YYYY-MM-DD')
      }
      const endpoint = modalType === 'time' ? 'time-step' : modalType === 'attr' ? 'coa-attribute/save' : 'metric-caliber'
      if (editingItem && editingItem.id && endpoint !== 'coa-attribute/save') {
        await apiClient.put(`/basic-param/${endpoint}/${editingItem.id}`, values)
      } else {
        await apiClient.post(`/basic-param/${endpoint}`, values)
      }
      message.success(editingItem ? '更新成功' : '创建成功')
      setModalVisible(false)
      if (modalType === 'time') fetchTimeStep()
      else if (modalType === 'attr') fetchAttrTree()
      else fetchCaliber()
    } catch (e: any) {
      message.error('操作失败: ' + (e.response?.data?.detail || e.message))
    }
  }

  // ===== 时间步列 =====
  const timeColumns = [
    { title: '步序', dataIndex: 'step_no', key: 'step_no', width: 80 },
    { title: '月份标签', dataIndex: 'month_label', key: 'month_label', width: 100 },
    {
      title: '月末日', dataIndex: 'month_end_date', key: 'month_end_date', width: 130,
      render: (v: string) => v ? dayjs(v).format('YYYY-MM-DD') : '-'
    },
    { title: '当月天数', dataIndex: 'month_days', key: 'month_days', width: 100 },
    { title: '当年天数', dataIndex: 'year_days', key: 'year_days', width: 100 },
    {
      title: '操作', key: 'action', width: 120,
      render: (_: any, r: any) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => handleEdit('time', r)} />
          <Popconfirm title="确认删除?" onConfirm={() => handleDelete('time', r.step_no)}>
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      )
    }
  ]

  // ===== 账户册属性列（树形）=====
  const attrColumns = [
    {
      title: '账户册编码', dataIndex: 'coa_cd', key: 'coa_cd', width: 180, ellipsis: true,
      render: (val: string, record: any) => (
        <span style={{ fontFamily: 'monospace', whiteSpace: 'nowrap' }}>{val}</span>
      )
    },
    {
      title: '账户册名称', dataIndex: 'coa_name', key: 'coa_name', ellipsis: true,
      render: (val: string, record: any) => (
        <Space>
          {record.has_data ? <FileTextOutlined style={{ color: '#1890ff' }} /> : <FolderOutlined style={{ color: '#999' }} />}
          <span style={{ color: record.has_data ? 'inherit' : '#999', whiteSpace: 'nowrap' }}>{val || '-'}</span>
        </Space>
      )
    },
    { title: '期限', dataIndex: 'term', key: 'term', width: 80, render: (v: string) => v || '-' },
    { title: '计息规则', dataIndex: 'accrule_base', key: 'accrule_base', width: 120, render: (v: string) => v || '-', ellipsis: true },
    { title: '收益率曲线', dataIndex: 'curve_name', key: 'curve_name', width: 180, render: (v: string) => v || '-', ellipsis: true },
    { title: '业务条线', dataIndex: 'business_line', key: 'business_line', width: 100, render: (v: string) => v || '-' },
    { title: '利率类型', dataIndex: 'replace_type', key: 'replace_type', width: 100, render: (v: string) => v || '-' },
    { title: '重定价频率', dataIndex: 'reprice_freq', key: 'reprice_freq', width: 100, render: (v: string) => v || '-' },
    {
      title: '操作', key: 'action', width: 80, fixed: 'right' as const,
      render: (_: any, record: any) => (
        <Button type="link" icon={<EditOutlined />} onClick={() => handleEdit('attr', record)}>
          {record.has_data ? '编辑' : '新增'}
        </Button>
      )
    }
  ]

  // ===== 报表口径列（参考报表口径.xlsx表头，23个指标分组表头） =====
  const caliberColumns: any[] = [
    {
      title: '账户册编码', dataIndex: 'coa_cd', key: 'coa_cd', width: 130, fixed: 'left' as const, ellipsis: true,
      render: (val: string) => <span style={{ fontFamily: 'monospace', whiteSpace: 'nowrap' }}>{val}</span>
    },
    {
      title: '账户册', dataIndex: 'coa_name', key: 'coa_name', width: 150, fixed: 'left' as const, ellipsis: true
    }
  ]
  // 动态生成23个指标列
  CALIBER_INDICATORS.forEach(ind => {
    const i = ind.key
    caliberColumns.push({
      title: `${i}. ${ind.name}`,
      children: [
        { title: '分子', dataIndex: `num${i}_name`, key: `num${i}`, width: 100, render: (v: string) => v || '-', ellipsis: true },
        { title: '分子系数', dataIndex: `num${i}_c`, key: `num${i}_c`, width: 70 },
        { title: '分子类型', dataIndex: `num${i}_t`, key: `num${i}_t`, width: 80 },
        { title: '分母', dataIndex: `den${i}_name`, key: `den${i}`, width: 100, render: (v: string) => v || '-', ellipsis: true },
        { title: '分母系数', dataIndex: `den${i}_c`, key: `den${i}_c`, width: 70 },
        { title: '分母类型', dataIndex: `den${i}_t`, key: `den${i}_t`, width: 80 }
      ]
    })
  })
  caliberColumns.push(
    { title: '备注', dataIndex: 'remark', key: 'remark', width: 150, render: (v: string) => v || '-', ellipsis: true },
    {
      title: '操作', key: 'action', width: 110, fixed: 'right' as const,
      render: (_: any, r: any) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => handleEdit('caliber', r)} />
          <Popconfirm title="确认删除?" onConfirm={() => handleDelete('caliber', r.id)}>
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      )
    }
  )

  const renderForm = () => {
    if (modalType === 'time') {
      return (
        <>
          <Form.Item name="step_no" label="步序" rules={[{ required: true }]}>
            <InputNumber style={{ width: '100%' }} min={1} max={120} />
          </Form.Item>
          <Form.Item name="month_label" label="月份标签" rules={[{ required: true }]}>
            <Input placeholder="例如: M1" />
          </Form.Item>
          <Form.Item name="month_end_date" label="月末日" rules={[{ required: true }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="month_days" label="当月天数">
            <InputNumber style={{ width: '100%' }} min={28} max={31} />
          </Form.Item>
          <Form.Item name="year_days" label="当年天数">
            <InputNumber style={{ width: '100%' }} min={360} max={366} />
          </Form.Item>
        </>
      )
    } else if (modalType === 'attr') {
      return (
        <>
          <Form.Item name="coa_cd" label="账户册编码" rules={[{ required: true }]}>
            <Input disabled placeholder="例如: 1_1_1" style={{ color: '#999' }} />
          </Form.Item>
          <Form.Item name="coa_name" label="账户册名称">
            <Input disabled style={{ color: '#999' }} />
          </Form.Item>
          <Form.Item name="term" label="期限">
            <Select
              showSearch
              allowClear
              placeholder="请选择期限"
              options={TERM_OPTIONS.map(t => ({ value: t, label: t }))}
            />
          </Form.Item>
          <Form.Item name="accrule_base" label="计息规则">
            <Select
              showSearch
              allowClear
              placeholder="请选择计息规则"
              options={ACCRULE_OPTIONS.map(t => ({ value: t, label: t }))}
            />
          </Form.Item>
          <Form.Item name="curve_id" label="收益率曲线ID">
            <Select
              showSearch
              allowClear
              placeholder="请选择曲线ID"
              options={curveOptions}
              onChange={handleCurveIdChange}
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
            />
          </Form.Item>
          <Form.Item name="curve_name" label="曲线名称">
            <Input disabled placeholder="选择曲线ID后自动带出" style={{ color: '#999' }} />
          </Form.Item>
          <Form.Item name="business_line" label="业务条线">
            <Select
              showSearch
              allowClear
              placeholder="请选择业务条线"
              options={BUSINESS_LINE_OPTIONS.map(t => ({ value: t, label: t }))}
            />
          </Form.Item>
          <Form.Item name="float_ratio" label="浮动比例">
            <InputNumber style={{ width: '100%' }} step={0.01} min={0} max={1} placeholder="0-1之间" />
          </Form.Item>
          <Form.Item name="replace_type" label="利率类型">
            <Select
              placeholder="请选择利率类型"
              options={REPLACE_TYPE_OPTIONS.map(t => ({ value: t, label: t }))}
            />
          </Form.Item>
          <Form.Item name="reprice_freq" label="重定价频率">
            <Select
              placeholder="请选择重定价频率"
              options={REPRICE_FREQ_OPTIONS.map(t => ({ value: t, label: t }))}
            />
          </Form.Item>
        </>
      )
    } else {
      return (
        <>
          <Form.Item name="coa_cd" label="账户册编码" rules={[{ required: true }]}>
            <Select
              showSearch
              allowClear
              placeholder="请选择账户册编码"
              options={coaOptions}
              onChange={handleCaliberCoaChange}
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
            />
          </Form.Item>
          <Form.Item name="coa_name" label="账户册名称">
            <Input disabled style={{ color: '#999' }} placeholder="选择编码后自动带出" />
          </Form.Item>
          {CALIBER_INDICATORS.map((ind, idx) => {
            const i = ind.key
            const colors = ['#1890ff', '#52c41a', '#fa8c16', '#722ed1', '#eb2f96', '#13c2c2', '#fa541c']
            const color = colors[idx % colors.length]
            return (
              <div key={i} style={{ borderTop: idx === 0 ? '1px solid #f0f0f0' : '1px dashed #f0f0f0', paddingTop: 8, marginTop: 8, marginBottom: 8 }}>
                <div style={{ color, fontWeight: 'bold', marginBottom: 8 }}>
                  {i}. {ind.name}
                </div>
                <Form.Item name={`num${i}`} label="分子项目" style={{ marginBottom: 8 }}>
                  <Select
                    showSearch
                    allowClear
                    placeholder="选择分子项目"
                    options={numDictOptions}
                    filterOption={(input, option) =>
                      (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                    }
                  />
                </Form.Item>
                <Form.Item name={`num${i}_c`} label="分子系数" style={{ marginBottom: 8 }}>
                  <InputNumber style={{ width: '100%' }} step={0.01} />
                </Form.Item>
                <Form.Item name={`num${i}_t`} label="分子取数类型" style={{ marginBottom: 8 }}>
                  <Select
                    showSearch
                    allowClear
                    placeholder="选择取数类型"
                    options={CALIBER_TYPE_OPTIONS}
                  />
                </Form.Item>
                <Form.Item name={`den${i}`} label="分母项目" style={{ marginBottom: 8 }}>
                  <Select
                    showSearch
                    allowClear
                    placeholder="选择分母项目"
                    options={denDictOptions}
                    filterOption={(input, option) =>
                      (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                    }
                  />
                </Form.Item>
                <Form.Item name={`den${i}_c`} label="分母系数" style={{ marginBottom: 8 }}>
                  <InputNumber style={{ width: '100%' }} step={0.01} />
                </Form.Item>
                <Form.Item name={`den${i}_t`} label="分母取数类型" style={{ marginBottom: 8 }}>
                  <Select
                    showSearch
                    allowClear
                    placeholder="选择取数类型"
                    options={CALIBER_TYPE_OPTIONS}
                  />
                </Form.Item>
              </div>
            )
          })}
          <Form.Item name="remark" label="备注" style={{ marginTop: 16 }}>
            <Input.TextArea rows={2} placeholder="说明该口径的业务含义" />
          </Form.Item>
        </>
      )
    }
  }

  const filteredCaliber = caliber.filter(c =>
    !search ||
    (c.coa_cd || '').includes(search) ||
    (c.coa_name || '').includes(search) ||
    (c.numerator || '').includes(search) ||
    (c.num2 || '').includes(search) ||
    (c.num3 || '').includes(search)
  )

  const items = [
    {
      key: '1',
      label: <span><ClockCircleOutlined /> 时间步设置 ({timeStep.length})</span>,
      children: (
        <div>
          <Space style={{ marginBottom: 16 }} wrap>
            <span>起始年月:</span>
            <Select
              value={stepYear}
              onChange={setStepYear}
              style={{ width: 100 }}
              options={Array.from({ length: 11 }, (_, i) => 2020 + i).map(y => ({ value: y, label: `${y}年` }))}
            />
            <Select
              value={stepMonth}
              onChange={setStepMonth}
              style={{ width: 90 }}
              options={Array.from({ length: 12 }, (_, i) => i + 1).map(m => ({ value: m, label: `${m}月` }))}
            />
            <Button type="primary" icon={<ReloadOutlined />} onClick={handleRegenerateTimeStep}>
              刷新（生成24个月M1-M24）
            </Button>
            <Button icon={<PlusOutlined />} onClick={() => handleAdd('time')}>新增</Button>
          </Space>
          <Table columns={timeColumns} dataSource={timeStep} rowKey="step_no" loading={loading} size="small" pagination={false} bordered />
        </div>
      )
    },
    {
      key: '2',
      label: <span><ProfileOutlined /> 账户册属性 ({attrTree.length})</span>,
      children: (
        <div>
          <Space style={{ marginBottom: 16 }}>
            <Button icon={<ReloadOutlined />} onClick={fetchAttrTree}>刷新</Button>
          </Space>
          <Table
            columns={attrColumns}
            dataSource={attrTree}
            rowKey="key"
            loading={loading}
            size="small"
            pagination={false}
            scroll={{ x: 1200, y: 500 }}
            bordered
            expandable={{
              indentSize: 20,
              expandedRowKeys: attrExpanded,
              onExpand: (expanded, record) => {
                setAttrExpanded(prev =>
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
      label: <span><FileSearchOutlined /> 报表口径 ({filteredCaliber.length})</span>,
      children: (
        <div>
          <Space style={{ marginBottom: 16 }}>
            <Input.Search
              placeholder="搜索账户册编码/名称/分子"
              allowClear
              style={{ width: 300 }}
              onChange={(e) => setSearch(e.target.value)}
            />
            <Button type="primary" icon={<PlusOutlined />} onClick={() => handleAdd('caliber')}>新增</Button>
            <Button icon={<ReloadOutlined />} onClick={fetchCaliber}>刷新</Button>
          </Space>
          <Table
            columns={caliberColumns}
            dataSource={filteredCaliber}
            rowKey="id"
            loading={loading}
            size="small"
            scroll={{ x: 9000, y: 500 }}
            pagination={{ pageSize: 50, showSizeChanger: true, showTotal: (t) => `共 ${t} 条` }}
            bordered
          />
        </div>
      )
    }
  ]

  return (
    <div>
      <h2>基础参数</h2>
      <Card>
        <Tabs items={items} activeKey={activeTab} onChange={setActiveTab} />
      </Card>

      <Modal
        title={editingItem ? '编辑' : '新增'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        destroyOnClose
        width={700}
      >
        <Form form={form} layout="vertical">
          {renderForm()}
        </Form>
      </Modal>
    </div>
  )
}

export default BasicParamPage