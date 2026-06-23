interface DataTableProps {
  data: Record<string, unknown>[]
}

export default function DataTable({ data }: DataTableProps) {
  if (!data || data.length === 0) {
    return <p className="text-gray-500 text-sm">No data available.</p>
  }

  const columns = Object.keys(data[0])

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm text-left border border-gray-700 rounded-lg overflow-hidden">
        <thead className="bg-gray-800 text-gray-300">
          <tr>
            <th className="px-3 py-2 border-b border-gray-700">#</th>
            {columns.map((col) => (
              <th key={col} className="px-3 py-2 border-b border-gray-700">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, idx) => (
            <tr key={idx} className="border-b border-gray-700 hover:bg-gray-800/50">
              <td className="px-3 py-2 text-gray-500">{idx + 1}</td>
              {columns.map((col) => (
                <td key={col} className="px-3 py-2">
                  {row[col] != null ? String(row[col]) : '—'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
