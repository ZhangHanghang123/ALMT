import { useState, useEffect, useRef } from 'react'
import { Table, Button, Space, Modal, Form, Input, InputNumber, message, Popconfirm, Card, Input as AntInput, Upload } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined, ReloadOutlined, FolderOutlined, FileTextOutlined, DownloadOutlined, UploadOutlined } from '@ant-design/icons'
import apiClient from '../api/client'

const { Search } = AntInput

interface TreeNode {
  key: string
  id?: number
  coa_cd: string
  coa_name: string | null
  balance: number | null
  average_balance: number | null
  rate: number | null
  has_data: boolean
  children?: TreeNode[]
}

const DataPage = () => {
  const [treeData, setTreeData] = useState<TreeNode[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [modalVisible, setModalVisible] = useState(false)
  const [editingItem, setEditingItem] = useState<any>(null)
  const [form] = Form.useForm()
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>([])
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

  const fetchTree = async () => {
    setLoading(true)
    try {
      const res = await apiClient.get('/position/tree')
      const data = Array.isArray(res.data) ? res.data : []
      console.log('Position tree loaded:', data.length, 'roots')
      const converted = convertKeys(data)
      setTreeData(converted)
      // 默认展开所有有子节点的节点
      setExpandedKeys(collectAllKeys(converted))
      setTableKey(k => k + 1)
    } catch (e: any) {
      console.error('Load error:', e)
      message.error('加载失败: ' + (e.response?.data?.detail || e.message || ''))
    } finally {
      setLoading(false)
    }
  }

  const convertKeys = (nodes: any[]): TreeNode[] => {
    return nodes.map(n => ({
      key: `coa_${n.id}`,
      id: n.id,
      coa_cd: n.coa_cd,
      coa_name: n.coa_name,
      balance: n.balance,
      average_balance: n.average_balance,
      rate: n.rate,
      has_data: n.has_data,
      children: n.children ? convertKeys(n.children) : []
    }))
  }

  const filterTree = (nodes: TreeNode[], keyword: string): TreeNode[] => {
    if (!keyword) return nodes
    const result: TreeNode[] = []
    for (const node of nodes) {
      const matchSelf = node.coa_cd?.includes(keyword) || node.coa_name?.includes(keyword)
      const filteredChildren = node.children ? filterTree(node.children, keyword) : []
      if (matchSelf || filteredChildren.length > 0) {
        result.push({ ...node, children: filteredChildren })
      }
    }
    return result
  }

  useEffect(() => { fetchTree() }, [])

  const displayData = search ? filterTree(treeData, search) : treeData

  const handleSearch = (value: string) => {
    setSearch(value)
  }

  const handleAdd = () => {
    setEditingItem(null)
    form.resetFields()
    setModalVisible(true)
  }

  const handleEdit = (record: TreeNode) => {
    if (!record.has_data) {
      message.warning('该账户册暂无数据，无需编辑')
      return
    }
    setEditingItem(record)
    form.setFieldsValue({
      coa_lvl: record.coa_cd,
      coa_name: record.coa_name,
      balance: record.balance,
      average_balance: record.average_balance,
      rate: record.rate
    })
    setModalVisible(true)
  }

  const handleDelete = async (record: TreeNode) => {
    if (!record.has_data) {
      message.warning('该账户册暂无数据')
      return
    }
    try {
      await apiClient.delete(`/position/${record.id}`)
      message.success('删除成功')
      fetchTree()
    } catch (e) {
      message.error('删除失败')
    }
  }

  const handleExport = async () => {
    try {
      const res = await apiClient.get('/position/export', { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', 'position.xlsx')
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
      message.success('导出成功')
    } catch (e: any) {
      message.error('导出失败: ' + (e.response?.data?.detail || e.message))
    }
  }

  const handleImport = async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    try {
      const res = await apiClient.post('/position/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      message.success(`导入成功: 新增 ${res.data.inserted} 条, 更新 ${res.data.updated} 条`)
      fetchTree()
    } catch (e: any) {
      message.error('导入失败: ' + (e.response?.data?.detail || e.message))
    }
    return false
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (editingItem && editingItem.id) {
        await apiClient.put(`/position/${editingItem.id}`, values)
        message.success('更新成功')
      } else {
        await apiClient.post('/position', values)
        message.success('创建成功')
      }
      setModalVisible(false)
      fetchTree()
    } catch (e: any) {
      message.error('操作失败: ' + (e.response?.data?.detail || e.message))
    }
  }

  const fmtMoney = (n: number | null) => {
    if (n === null || n === undefined) return '-'
    if (n >= 1e8) return (n / 1e8).toFixed(2) + ' 亿'
    if (n >= 1e4) return (n / 1e4).toFixed(2) + ' 万'
    return (n || 0).toFixed(2)
  }

  const columns = [
    {
      title: '层级编码',
      dataIndex: 'coa_cd',
      key: 'coa_cd',
      width: 180,
      ellipsis: true,
      render: (val: string) => (
        <span style={{ fontFamily: 'monospace', whiteSpace: 'nowrap' }}>{val}</span>
      )
    },
    {
      title: '账户册名称',
      dataIndex: 'coa_name',
      key: 'coa_name',
      ellipsis: true,
      render: (val: string, record: TreeNode) => (
        <Space>
          {record.has_data ? <FileTextOutlined style={{ color: '#1890ff' }} /> : <FolderOutlined style={{ color: '#999' }} />}
          <span style={{ color: record.has_data ? 'inherit' : '#999', whiteSpace: 'nowrap' }}>{val || '-'}</span>
        </Space>
      )
    },
    {
      title: '余额',
      dataIndex: 'balance',
      key: 'balance',
      width: 150,
      align: 'right' as const,
      render: (val: number | null, record: TreeNode) => (
        <span style={{
          color: record.has_data ? 'inherit' : '#bbb',
          fontWeight: record.balance && Number(record.balance) >= 1e8 ? 'bold' : 'normal'
        }}>
          {record.has_data && val !== null ? fmtMoney(val) : '-'}
        </span>
      )
    },
    {
      title: '日均余额',
      dataIndex: 'average_balance',
      key: 'average_balance',
      width: 150,
      align: 'right' as const,
      render: (val: number | null, record: TreeNode) => (
        <span style={{ color: record.has_data ? 'inherit' : '#bbb' }}>
          {record.has_data && val !== null ? fmtMoney(val) : '-'}
        </span>
      )
    },
    {
      title: '利率',
      dataIndex: 'rate',
      key: 'rate',
      width: 120,
      align: 'right' as const,
      render: (val: number | null, record: TreeNode) => {
        if (!record.has_data || val === null) return <span style={{ color: '#bbb' }}>-</span>
        // 值<1 当作小数百分比，>1 当作绝对值显示
        if (val > 0 && val < 1) return (Number(val) * 100).toFixed(2) + '%'
        return val.toFixed(2)
      }
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_: any, record: TreeNode) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
            disabled={!record.has_data}
          />
          <Popconfirm title="确认删除?" onConfirm={() => handleDelete(record)}>
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
              disabled={!record.has_data}
            />
          </Popconfirm>
        </Space>
      )
    }
  ]

  return (
    <div>
      <Card
        title="存量数据（按账户册结构）"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={fetchTree}>刷新</Button>
            <Button icon={<DownloadOutlined />} onClick={handleExport}>导出Excel</Button>
            <Upload beforeUpload={handleImport} showUploadList={false} accept=".xlsx,.xls">
              <Button icon={<UploadOutlined />}>导入Excel</Button>
            </Upload>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>新增</Button>
          </Space>
        }
      >
        <Space style={{ marginBottom: 16 }}>
          <Search
            placeholder="搜索账户册编码或名称"
            onSearch={handleSearch}
            style={{ width: 300 }}
            allowClear
          />
        </Space>

        <Table
          key={tableKey}
          columns={columns}
          dataSource={displayData}
          rowKey="key"
          loading={loading}
          size="small"
          pagination={false}
          scroll={{ x: 1000, y: 600 }}
          bordered
          expandable={{
            indentSize: 20,
            expandedRowKeys: expandedKeys,
            onExpand: (expanded, record) => {
              setExpandedKeys(prev =>
                expanded ? [...prev, record.key] : prev.filter(k => k !== record.key)
              )
            }
          }}
        />
      </Card>

      <Modal
        title={editingItem?.id ? '编辑存量数据' : '新增存量数据'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        destroyOnClose
        width={500}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="coa_lvl" label="账户册编码" rules={[{ required: true }]}>
            <Input placeholder="例如: 1_1_1_2" disabled={!!editingItem?.id} />
          </Form.Item>
          <Form.Item name="coa_name" label="账户册名称">
            <Input />
          </Form.Item>
          <Form.Item name="balance" label="余额">
            <InputNumber style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="average_balance" label="日均余额">
            <InputNumber style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="rate" label="利率">
            <InputNumber style={{ width: '100%' }} step={0.0001} min={0} max={1} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default DataPage